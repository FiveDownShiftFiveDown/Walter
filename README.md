# Walter (desktop)

Walter's money module as a Windows app. Data saves automatically to
`Documents\Walter\walter-data.json`, with a dated copy each day in `Documents\Walter\backups` (last 30 kept).

## How an update goes out

1. Change `src/walter.html` (the same page as the web version).
2. Bump `"version"` in `src-tauri/tauri.conf.json` (for example 1.0.0 → 1.0.1).
3. Push it to the `release` branch (or run **Actions → Build Walter → Run workflow**).
4. When it finishes, a **draft** release appears under **Releases**. Download the installer from it and try it.
5. Happy with it? Open the draft and click **Publish release**. Every installed copy sees the update
   within a few hours (or right away from More → Check for updates) and shows an "Install and restart" bar.

## Pieces

- `src/walter.html`: the Walter page.
- `tools/build.py`: turns it into `dist/index.html` with desktop saving and the update bar added.
- `src-tauri/`: the app shell (Rust/Tauri): file saving, backups, and the updater.
- `tools/make_icons.py`: draws the icon.

The update-signing key lives in the repo's Actions secrets (`TAURI_SIGNING_PRIVATE_KEY`,
`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`). Keep your own copy somewhere safe. Without it, installed copies can't be
updated and everyone would have to reinstall.
