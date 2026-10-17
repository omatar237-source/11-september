"""Paint a moody detective office with a pinned world map on the wall.

Usage: python make_background.py <countries.geojson> <out.png>
Output is 1024x576 (matches the video), rendered at 2x then downscaled.
"""
import json
import sys

import cv2
import numpy as np

SCALE = 2
W, H = 1024 * SCALE, 576 * SCALE
rng = np.random.default_rng(7)


def s(v):
    return int(round(v * SCALE))


def wood_wall():
    img = np.zeros((H, W, 3), np.float32)
    plank_w = s(64)
    for i, x in enumerate(range(0, W, plank_w)):
        tone = 0.85 + 0.3 * rng.random()
        base = np.array([30, 42, 62], np.float32) * tone  # BGR dark walnut
        img[:, x:x + plank_w] = base
        cv2.line(img, (x, 0), (x, H), (12, 16, 22), s(2))
    # grain: stretched vertical noise
    noise = rng.normal(0, 1, (H // 40, W)).astype(np.float32)
    noise = cv2.resize(noise, (W, H), interpolation=cv2.INTER_CUBIC)
    noise = cv2.GaussianBlur(noise, (0, 0), sigmaX=1.2 * SCALE, sigmaY=6 * SCALE)
    img += noise[..., None] * 9
    # wainscot rail and darker lower panel
    rail_y = s(470)
    img[rail_y:] *= 0.6
    cv2.rectangle(img, (0, rail_y - s(10)), (W, rail_y), (40, 62, 92), -1)
    cv2.line(img, (0, rail_y), (W, rail_y), (10, 14, 20), s(2))
    return img


def load_polys(path):
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    polys = []
    for feat in gj["features"]:
        g = feat["geometry"]
        if g is None:
            continue
        parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for p in parts:
            polys.append(np.array(p[0], np.float64))
    return polys


def draw_map(polys, mw, mh, lat_top=80, lat_bot=-58):
    def proj(lon, lat):
        x = (lon + 180) / 360 * mw
        y = (lat_top - lat) / (lat_top - lat_bot) * mh
        return x, y

    # aged parchment
    paper = np.full((mh, mw, 3), (150, 196, 222), np.float32)
    blotch = cv2.GaussianBlur(rng.normal(0, 1, (mh, mw)).astype(np.float32), (0, 0), s(18))
    blotch /= np.abs(blotch).max() + 1e-6
    paper += blotch[..., None] * np.array([18, 20, 16])
    fine = rng.normal(0, 4, (mh, mw, 1)).astype(np.float32)
    paper += fine

    land = np.zeros((mh, mw), np.uint8)
    outlines = []
    for p in polys:
        x, y = proj(p[:, 0], p[:, 1])
        pts = np.stack([x, y], 1).round().astype(np.int32)
        cv2.fillPoly(land, [pts], 255)
        outlines.append(pts)
    landf = cv2.GaussianBlur(land.astype(np.float32) / 255, (0, 0), 0.8)[..., None]
    paper = paper * (1 - landf) + (paper * np.array([0.70, 0.80, 0.86])) * landf
    # graticule
    for lon in range(-180, 181, 30):
        x, _ = proj(lon, 0)
        cv2.line(paper, (int(x), 0), (int(x), mh), (110, 140, 160), 1, cv2.LINE_AA)
    for lat in range(-60, 81, 20):
        _, y = proj(0, lat)
        cv2.line(paper, (0, int(y)), (mw, int(y)), (110, 140, 160), 1, cv2.LINE_AA)
    cv2.polylines(paper, outlines, True, (40, 62, 88), max(1, SCALE), cv2.LINE_AA)
    # burnt, darker edges
    yy, xx = np.mgrid[0:mh, 0:mw].astype(np.float32)
    d = np.minimum.reduce([xx, yy, mw - xx, mh - yy]) / s(40)
    paper *= (0.55 + 0.45 * np.clip(d, 0, 1))[..., None]
    return paper, proj


def paste(dst, src, x, y):
    h, w = src.shape[:2]
    dst[y:y + h, x:x + w] = src


def drop_shadow(img, x0, y0, x1, y1, off=s(8), blur=s(10), strength=0.6):
    m = np.zeros(img.shape[:2], np.float32)
    cv2.rectangle(m, (x0 + off, y0 + off), (x1 + off, y1 + off), 1, -1)
    m = cv2.GaussianBlur(m, (0, 0), blur)
    img *= (1 - strength * m)[..., None]


def pin(img, x, y, color=(30, 30, 200)):
    cv2.circle(img, (x + s(2), y + s(3)), s(6), (10, 10, 10), -1, cv2.LINE_AA)
    cv2.circle(img, (x, y), s(6), color, -1, cv2.LINE_AA)
    cv2.circle(img, (x - s(2), y - s(2)), s(2), (200, 200, 255), -1, cv2.LINE_AA)


def note(img, cx, cy, w, h, angle, color, lines=3):
    card = np.zeros((h, w, 3), np.float32)
    card[:] = color
    for i in range(lines):
        yy = s(14) + i * s(11)
        if yy < h - s(6):
            cv2.line(card, (s(8), yy), (w - s(8) - int(rng.integers(0, w // 3)), yy),
                     (60, 60, 70), max(1, SCALE // 2 + 1), cv2.LINE_AA)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1)
    big = int(np.hypot(w, h)) + 2
    M[0, 2] += (big - w) / 2
    M[1, 2] += (big - h) / 2
    rot = cv2.warpAffine(card, M, (big, big))
    mask = cv2.warpAffine(np.ones((h, w), np.float32), M, (big, big))
    x0, y0 = cx - big // 2, cy - big // 2
    shadow = cv2.GaussianBlur(mask, (0, 0), s(4))
    region = img[y0 + s(5):y0 + s(5) + big, x0 + s(5):x0 + s(5) + big]
    region *= (1 - 0.5 * shadow)[..., None]
    region = img[y0:y0 + big, x0:x0 + big]
    region[:] = region * (1 - mask[..., None]) + rot * mask[..., None]
    pin(img, cx, cy - h // 2 + s(6), (40, 160, 220))


def main(geojson, out):
    img = wood_wall()

    # --- framed world map ---
    mx0, my0, mx1, my1 = s(150), s(48), s(874), s(420)
    frame = s(14)
    drop_shadow(img, mx0 - frame, my0 - frame, mx1 + frame, my1 + frame, off=s(10), blur=s(14), strength=0.7)
    cv2.rectangle(img, (mx0 - frame, my0 - frame), (mx1 + frame, my1 + frame), (22, 38, 58), -1)
    cv2.rectangle(img, (mx0 - frame, my0 - frame), (mx1 + frame, my1 + frame), (45, 75, 105), s(2))
    cv2.rectangle(img, (mx0 - 2, my0 - 2), (mx1 + 2, my1 + 2), (8, 12, 18), s(2))
    paper, proj = draw_map(load_polys(geojson), mx1 - mx0, my1 - my0)
    paste(img, paper, mx0, my0)

    # --- case pins + red string ---
    cities = {
        "london": (-0.1, 51.5), "new_york": (-74.0, 40.7), "cairo": (31.2, 30.0),
        "moscow": (37.6, 55.8), "dubai": (55.3, 25.2), "tokyo": (139.7, 35.7),
        "rio": (-43.2, -22.9), "cape_town": (18.4, -33.9), "sydney": (151.2, -33.9),
        "istanbul": (29.0, 41.0), "mexico": (-99.1, 19.4), "singapore": (103.8, 1.3),
    }
    pts = {}
    for k, (lon, lat) in cities.items():
        x, y = proj(lon, lat)
        pts[k] = (mx0 + int(x), my0 + int(y))
    links = [("new_york", "london"), ("london", "cairo"), ("cairo", "dubai"), ("dubai", "singapore"),
             ("singapore", "tokyo"), ("istanbul", "moscow"), ("london", "istanbul"), ("cairo", "cape_town"),
             ("new_york", "rio"), ("mexico", "new_york"), ("singapore", "sydney"), ("rio", "cape_town")]
    for a, b in links:
        (x0, y0), (x1, y1) = pts[a], pts[b]
        cv2.line(img, (x0 + s(2), y0 + s(3)), (x1 + s(2), y1 + s(3)), (15, 15, 20), s(2), cv2.LINE_AA)
        cv2.line(img, (x0, y0), (x1, y1), (35, 25, 175), s(2), cv2.LINE_AA)
    for p in pts.values():
        pin(img, *p)

    # --- clipped notes / photos around the map ---
    note(img, s(80), s(150), s(80), s(60), 6, (120, 220, 245))
    note(img, s(78), s(300), s(84), s(96), -4, (210, 215, 220), lines=0)  # "photo"
    note(img, s(948), s(140), s(84), s(64), -7, (205, 225, 235))
    note(img, s(950), s(300), s(80), s(96), 5, (200, 205, 210), lines=0)
    note(img, s(830), s(400), s(70), s(52), 9, (150, 210, 240))

    # --- noir lighting ---
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # warm pool from an off-frame desk lamp, upper-left of centre
    lamp = np.exp(-(((xx - s(330)) / s(520)) ** 2 + ((yy - s(170)) / s(380)) ** 2))
    light = 0.28 + 1.05 * lamp
    # venetian-blind shadows falling diagonally from the right
    t = (xx * 0.42 + yy) / s(34)
    blinds = 0.5 + 0.5 * np.sin(t * 2 * np.pi)
    blinds = np.clip((blinds - 0.35) * 3, 0, 1)
    blinds = cv2.GaussianBlur(blinds, (0, 0), s(3))
    fall = np.clip((xx - s(380)) / s(500), 0, 1)  # only on the right half
    light *= 1 - 0.38 * blinds * fall
    img *= light[..., None]
    img *= np.array([0.80, 0.95, 1.12])  # warm amber cast (BGR)

    # vignette
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H * 0.45) / (H / 2)) ** 2)
    img *= np.clip(1.15 - 0.55 * r ** 1.6, 0.15, 1)[..., None]

    img = np.clip(img, 0, 255).astype(np.uint8)
    img = cv2.resize(img, (W // SCALE, H // SCALE), interpolation=cv2.INTER_AREA)
    cv2.imwrite(out, img)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
