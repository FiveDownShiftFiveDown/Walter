"""Builds dist/index.html (the desktop page) from src/walter.html.

The desktop page is Walter exactly as on the web, plus:
  - it loads from Documents\\Walter\\walter-data.json (handed in by the app before the page runs)
  - every save also goes to that file
  - a "This computer" card in More (open folder, version, check for updates)
  - an update bar that appears when a new version is ready

Every edit below is an exact-match replacement, so if walter.html changes shape the
build stops with a clear message instead of shipping a broken app.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / "src" / "walter.html").read_text(encoding="utf-8")


def swap(text, old, new, label):
    n = text.count(old)
    if n != 1:
        sys.exit(f"build.py: expected exactly one match for [{label}], found {n}")
    return text.replace(old, new)


DESK_CSS = """
#deskbar{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap;padding:8px 16px;background:var(--accent-bg);border-bottom:1px solid var(--line);font-size:14px}
#deskbar[hidden]{display:none}
#deskbar.bad{background:var(--bad-bg);color:var(--bad)}
#deskbar .btn{flex:0 0 auto}
"""

DESK_JS = r"""<script>
/* ---------- desktop bridge: file saving + updates ---------- */
(function(){
"use strict";
const D = window.__WALTER_DESK__, T = window.__TAURI__;
if (!D || !T || !T.core) return;
const invoke = T.core.invoke;
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let timer = null, pending = null, busy = false, retry = null;
const W = window.walterDesk = {
  status: {checking:false, available:null, installing:false, msg:''},
  saveError: null,
  save(obj){ pending = JSON.stringify(obj); clearTimeout(timer); timer = setTimeout(flush, 250); },
  openFolder(){ invoke('open_data_folder').catch(e => { W.saveError = 'Could not open the folder: ' + e; paint(); }); },
  async check(manual){
    const s = W.status;
    if (s.checking || s.installing) return;
    s.checking = true; if (manual) s.msg = 'Checking for updates…'; paint();
    try {
      const u = await invoke('check_update');
      s.available = u ? u.version : null;
      s.msg = u ? 'Version ' + u.version + ' is ready to install.' : (manual ? "You're on the latest version." : s.msg);
    } catch (e) {
      if (manual) s.msg = "Couldn't reach the update server. Check your internet and try again.";
    }
    s.checking = false; paint();
  },
  async install(){
    const s = W.status;
    if (s.installing) return;
    s.installing = true; s.msg = 'Downloading the update. Walter will restart by itself.'; paint();
    try { clearTimeout(timer); await flush(); await invoke('install_update'); }
    catch (e) { s.installing = false; s.msg = "The update didn't install. Try again in a minute."; paint(); }
  }
};
async function flush(){
  if (busy || pending == null) return;
  busy = true;
  const c = pending; pending = null;
  try { await invoke('save_data', {contents:c}); W.saveError = null; }
  catch (e) {
    W.saveError = "Walter couldn't save to your Documents folder (" + e + "). It will keep trying.";
    if (pending == null) pending = c;
    clearTimeout(retry); retry = setTimeout(flush, 5000);
  }
  busy = false;
  paint();
  if (pending != null && !W.saveError) flush();
}
function paint(){
  const bar = document.getElementById('deskbar'), s = W.status;
  if (bar) {
    if (W.saveError) {
      bar.className = 'bad'; bar.hidden = false; bar.innerHTML = '<span>' + esc(W.saveError) + '</span>';
    } else if (s.available) {
      bar.className = ''; bar.hidden = false;
      bar.innerHTML = '<span><b>Walter ' + esc(s.available) + '</b> is ready to install.</span><button type="button" class="btn sm"' + (s.installing ? ' disabled' : '') + '>' + (s.installing ? 'Installing…' : 'Install and restart') + '</button>';
      const b = bar.querySelector('button'); if (b) b.onclick = () => W.install();
    } else { bar.hidden = true; bar.innerHTML = ''; }
  }
  const m = document.getElementById('deskUpd'); if (m) m.textContent = s.msg || '';
}
W.paint = paint;
setTimeout(() => W.check(false), 4000);
setInterval(() => W.check(false), 6 * 60 * 60 * 1000);
})();
</script>
"""

out = src
if not out.lstrip().lower().startswith("<!doctype"):
    out = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n') + out
out = swap(out, "</style>", DESK_CSS + "</style>", "end of style")
out = swap(out, '<div id="app"></div>', '<div id="deskbar" hidden></div>\n<div id="app"></div>', "app root")
out = swap(out, "\n<script>\n(function(){", "\n" + DESK_JS + "<script>\n(function(){", "main script start")

# Load: prefer the Documents file unless this window holds something newer.
out = swap(out,
    "let storageOK = true;\nlet state = defaultState();\ntry { const raw = localStorage.getItem(KEY);",
    "let storageOK = true;\n"
    "const DESK = window.__WALTER_DESK__ || null;\n"
    "function deskPick(localRaw, localSaved){\n"
    "  if (!DESK || !DESK.file) return localRaw;\n"
    "  try { const f = JSON.parse(DESK.file); if (f && f.app === 'walter' && f.state && (!localRaw || !localSaved || (f.savedAt || '') >= localSaved)) return JSON.stringify(f.state); } catch (e) {}\n"
    "  return localRaw;\n"
    "}\n"
    "let state = defaultState();\n"
    "try { const raw = deskPick(localStorage.getItem(KEY), localStorage.getItem(KEY + '-saved'));",
    "load")

# Save: same as the web, plus a timestamp and the file.
out = swap(out,
    "function save(){ try { localStorage.setItem(KEY, JSON.stringify(state)); storageOK = true; } catch (e) { storageOK = false; } }",
    "function save(){ const at = new Date().toISOString(); try { localStorage.setItem(KEY, JSON.stringify(state)); localStorage.setItem(KEY + '-saved', at); storageOK = true; } catch (e) { storageOK = false; }"
    " if (DESK && window.walterDesk) window.walterDesk.save({app:'walter', v:1, savedAt:at, state}); }",
    "save")

# More tab: desktop card + backup wording.
out = swap(out,
    "<p class=\"small\">Walter saves on this device only. A backup code holds everything in one block of text. Keep it in Notes or text it to yourself, and paste it back on any device to pick up where you left off.</p>",
    "<p class=\"small\">${DESK ? 'A backup code holds everything in one block of text. Use one to move Walter to your phone or another computer: make it here, paste it in there.' : 'Walter saves on this device only. A backup code holds everything in one block of text. Keep it in Notes or text it to yourself, and paste it back on any device to pick up where you left off.'}</p>",
    "backup wording")
out = swap(out,
    "    ${owedSection()}\n    <section class=\"card\"><h2>Backup</h2>",
    "    ${owedSection()}\n"
    "    ${DESK ? `<section class=\"card\"><h2>This computer</h2>\n"
    "      <p class=\"small\">Walter saves by itself, every time you change something, to <b style=\"word-break:break-all\">${E(DESK.path || 'Documents\\\\Walter\\\\walter-data.json')}</b>. A copy from each day goes in the <b>backups</b> folder next to it, and the last 30 days are kept.</p>\n"
    "      <button type=\"button\" class=\"btn sm secondary\" data-act=\"deskOpen\">Open the Walter folder</button>\n"
    "      <p class=\"hint\">Version ${E(DESK.version || '')}. <span id=\"deskUpd\">${E((window.walterDesk && window.walterDesk.status.msg) || '')}</span></p>\n"
    "      <button type=\"button\" class=\"btn sm secondary\" data-act=\"deskCheck\">Check for updates</button></section>` : ''}\n"
    "    <section class=\"card\"><h2>Backup</h2>",
    "desktop card")

out = swap(out,
    "const ACT = {\n",
    "const ACT = {\n"
    "  deskOpen: () => { if (window.walterDesk) window.walterDesk.openFolder(); },\n"
    "  deskCheck: () => { if (window.walterDesk) window.walterDesk.check(true); },\n",
    "actions")

dist = ROOT / "dist"
dist.mkdir(exist_ok=True)
(dist / "index.html").write_text(out, encoding="utf-8")
print(f"build.py: wrote dist/index.html ({len(out):,} bytes)")
