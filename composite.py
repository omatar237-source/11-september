"""Key out the green screen and composite the speaker into the detective room.

Usage: python composite.py <input.mp4> <background.png> <out.mp4> <ffmpeg_bin_dir> [preview.png]
"""
import os
import subprocess
import sys

import cv2
import numpy as np


def green_columns(frame):
    """Columns where the green screen is (garbage matte for the studio gear at the sides)."""
    b, g, r = [frame[..., i].astype(np.int16) for i in range(3)]
    greenish = (g - np.maximum(r, b)) > 40
    frac = greenish.mean(axis=0)
    cols = np.where(frac > 0.35)[0]
    return int(cols.min()), int(cols.max())


def guided_filter(guide, src, radius, eps):
    """Edge-aware smoothing: snaps the blocky matte to the sharp luma edges."""
    k = (2 * radius + 1, 2 * radius + 1)
    mean_i = cv2.boxFilter(guide, -1, k)
    mean_p = cv2.boxFilter(src, -1, k)
    cov_ip = cv2.boxFilter(guide * src, -1, k) - mean_i * mean_p
    var_i = cv2.boxFilter(guide * guide, -1, k) - mean_i * mean_i
    a = cov_ip / (var_i + eps)
    b = mean_p - a * mean_i
    return cv2.boxFilter(a, -1, k) * guide + cv2.boxFilter(b, -1, k)


def key(frame, x0, x1, prev_alpha=None):
    f = frame.astype(np.float32)
    b, g, r = f[..., 0], f[..., 1], f[..., 2]
    # WhatsApp video stores colour at half resolution in blocky chunks; smooth the
    # green signal first so the matte doesn't inherit those stair-steps
    diff = cv2.GaussianBlur(g - np.maximum(r, b), (0, 0), 1.4)
    alpha = 1 - np.clip((diff - 22) / (50 - 22), 0, 1)
    # garbage matte: anything outside the green screen is studio, never the speaker
    pad = 6
    alpha[:, : x0 + pad] = 0
    alpha[:, x1 - pad:] = 0
    # clean speckles and soften the edge a touch
    hard = (alpha > 0.5).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(hard, 8)
    if n > 1:
        keep = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        body = cv2.dilate((lab == keep).astype(np.uint8), np.ones((9, 9), np.uint8))
        alpha *= body
    # refine against the full-resolution brightness, then choke slightly so no
    # green-screen pixels survive at the rim
    luma = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    alpha = guided_filter(luma, alpha, 3, 2e-3)
    alpha = np.clip((alpha - 0.12) / 0.80, 0, 1)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.6)
    # light temporal smoothing to stop the edge from shimmering frame to frame
    if prev_alpha is not None:
        alpha = 0.7 * alpha + 0.3 * prev_alpha

    # spill suppression: green can't exceed the average of red and blue
    lim = (r + b) / 2 + 6
    g2 = np.minimum(g, lim)
    fg = np.stack([b, g2, r], -1)

    # edge decontamination: rim pixels are a mix of person + green screen, which
    # turns into a dark/grey outline. Replace them with colour pulled from inside.
    core = cv2.erode((alpha > 0.98).astype(np.float32), np.ones((3, 3), np.uint8))
    num = cv2.GaussianBlur(fg * core[..., None], (0, 0), 3)
    den = cv2.GaussianBlur(core, (0, 0), 3)[..., None]
    inside = num / np.maximum(den, 1e-4)
    t = np.clip((alpha - 0.5) / 0.48, 0, 1)[..., None]  # 0 at rim, 1 well inside
    t = np.where(den > 1e-3, t, 1)
    fg = fg * t + inside * (1 - t)
    return fg, alpha


def grade_speaker(fg, alpha, light_map):
    """Re-light the speaker to sit in a dim, lamp-lit room."""
    h, w = alpha.shape
    out = fg / 255.0
    # slightly lower exposure and add contrast
    out = np.clip((out - 0.5) * 1.12 + 0.5, 0, 1) * 0.86
    # same warm amber cast as the room (BGR)
    out *= np.array([0.80, 0.93, 1.08])
    # key light from the lamp side (upper-left), falloff to the right
    out *= light_map[..., None]
    # tiny lift of shadows toward warm brown so blacks are not dead
    out = out * 0.96 + np.array([0.010, 0.016, 0.026])
    return np.clip(out * 255, 0, 255)


def main(src, bg_path, out_path, ffbin, preview=None, preview_frame="0"):
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    bg = cv2.imread(bg_path).astype(np.float32)
    bg = cv2.resize(bg, (w, h))
    # shallow depth of field: room slightly soft behind the speaker
    bg = cv2.GaussianBlur(bg, (0, 0), 1.6)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lamp = np.exp(-(((xx - w * 0.30) / (w * 0.55)) ** 2 + ((yy - h * 0.25) / (h * 0.9)) ** 2))
    light_map = 0.62 + 0.55 * lamp
    rim_dir = np.clip((w * 0.5 - xx) / (w * 0.5), 0, 1)  # rim glow on the lamp side
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.45) / (h / 2)) ** 2)
    vignette = np.clip(1.12 - 0.42 * r ** 1.8, 0.25, 1)[..., None]

    ok, first = cap.read()
    x0, x1 = green_columns(first)
    print(f"green screen columns: {x0}..{x1}", flush=True)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    ffmpeg = os.path.join(ffbin, "ffmpeg.exe")
    proc = None
    if not preview:
        proc = subprocess.Popen([
            ffmpeg, "-v", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
            "-i", src, "-map", "0:v", "-map", "1:a?", "-c:a", "copy",
            "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-shortest", out_path,
        ], stdin=subprocess.PIPE)

    rng = np.random.default_rng(1)
    i = 0
    prev_alpha = None
    pf = int(preview_frame)
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if preview and i < pf:
            i += 1
            continue
        fg, alpha = key(frame, x0, x1, prev_alpha)
        prev_alpha = alpha
        fg = grade_speaker(fg, alpha, light_map)

        # warm rim / light-wrap: let the lamp-lit wall bleed onto the speaker's edge
        edge = np.clip(cv2.GaussianBlur(alpha, (0, 0), 4) - alpha * 0.0, 0, 1) * (1 - alpha)
        inner = alpha - cv2.erode(alpha, np.ones((7, 7), np.uint8))
        inner = cv2.GaussianBlur(np.clip(inner, 0, 1), (0, 0), 2.5)
        wrap = cv2.GaussianBlur(bg, (0, 0), 6)
        fg = fg * (1 - 0.2 * inner[..., None]) + wrap * 0.2 * inner[..., None]
        fg += (inner * rim_dir)[..., None] * np.array([20, 55, 95])

        # soft contact shadow of the speaker on the wall (offset right/down, away from the lamp)
        M = np.float32([[1, 0, 22], [0, 1, 10]])
        sh = cv2.warpAffine(alpha, M, (w, h))
        sh = cv2.GaussianBlur(sh, (0, 0), 18)
        room = bg * (1 - 0.35 * sh[..., None])

        a = alpha[..., None]
        comp = fg * a + room * (1 - a)
        comp *= vignette
        comp += rng.normal(0, 3.0, (h, w, 1))  # light film grain
        comp = np.clip(comp, 0, 255).astype(np.uint8)

        if preview:
            cv2.imwrite(preview, comp)
            break
        proc.stdin.write(comp.tobytes())
        i += 1
        if i % 60 == 0:
            print(f"{i} frames", flush=True)

    cap.release()
    if proc:
        proc.stdin.close()
        proc.wait()
        print(f"done: {i} frames -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:])
