# 11-september

Cinematic detective-board scene (16:9). Open `detective-board.html` in Chrome or Edge, type the names, then click **تسجيل وتنزيل** to export the video.

- `template.html` – source; run `build.ps1` to rebuild `detective-board.html` (embeds `images/`).

## Auto-sync

Every change in this folder is committed and pushed to GitHub automatically (about 10 seconds after you stop editing), and changes from other PCs are pulled every 5 minutes.

On a new PC, after `git clone`, run once:

    powershell -ExecutionPolicy Bypass -File install-autosync.ps1

Turn it off: add `-Remove` to that command. Activity is written to `autosync.log`.
