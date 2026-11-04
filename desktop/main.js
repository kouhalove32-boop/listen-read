// 聞き読みプレーヤー for Windows: serves the web app + bundled audio from app://listen-read/
const { app, BrowserWindow, protocol, net, shell, Menu, ipcMain, nativeImage, screen } = require('electron');
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');

protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true, corsEnabled: true } },
]);

const ROOT = app.isPackaged ? path.join(process.resourcesPath, 'web') : path.join(__dirname, 'web');
const ASSETS = path.join(__dirname, 'assets');
if (!app.requestSingleInstanceLock()) app.quit();
app.setAppUserModelId('io.github.kouhalove32.listenread');

// ---------- window state (size, position, maximized, zoom) ----------
const STATE_FILE = () => path.join(app.getPath('userData'), 'window-state.json');
function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE(), 'utf8')); } catch { return {}; }
}
let state = {};
function saveState() {
  if (!win) return;
  const s = { ...state, maximized: win.isMaximized(), zoom: win.webContents.getZoomLevel() };
  if (!win.isMaximized() && !win.isMinimized() && !win.isFullScreen()) s.bounds = win.getBounds();
  state = s;
  try { fs.writeFileSync(STATE_FILE(), JSON.stringify(s)); } catch {}
}
function initialBounds() {
  const wa = screen.getPrimaryDisplay().workArea;
  const b = state.bounds;
  if (b && screen.getAllDisplays().some((d) => {
    const a = d.workArea;
    return b.x < a.x + a.width - 100 && b.x + b.width > a.x + 100 && b.y >= a.y - 20 && b.y < a.y + a.height - 100;
  })) return b;
  const width = Math.min(1440, Math.round(wa.width * 0.85));
  const height = Math.min(940, Math.round(wa.height * 0.88));
  return { width, height, x: wa.x + Math.round((wa.width - width) / 2), y: wa.y + Math.round((wa.height - height) / 2) };
}

// ---------- taskbar ----------
const icon = (n) => nativeImage.createFromPath(path.join(ASSETS, n + '.png'));
let playing = false;
function thumbar() {
  if (!win || process.platform !== 'win32') return;
  const send = (c) => () => win.webContents.send('player-command', c);
  win.setThumbarButtons([
    { tooltip: '前の文', icon: icon('prev'), click: send('prev') },
    { tooltip: playing ? '一時停止' : '再生', icon: icon(playing ? 'pause' : 'play'), click: send('play') },
    { tooltip: '次の文', icon: icon('next'), click: send('next') },
  ]);
}
ipcMain.on('app-version', (e) => { e.returnValue = app.getVersion(); });
ipcMain.on('player-state', (_e, s) => {
  if (!win) return;
  win.setProgressBar(s.playing ? Math.max(0.01, Math.min(1, s.progress)) : -1);
  if (s.playing !== playing) { playing = s.playing; thumbar(); }
});

// ---------- right-click menu ----------
function contextMenu(params) {
  const t = [];
  if (params.isEditable) {
    t.push({ role: 'undo', label: '元に戻す' }, { role: 'redo', label: 'やり直し' }, { type: 'separator' },
      { role: 'cut', label: '切り取り' }, { role: 'copy', label: 'コピー' }, { role: 'paste', label: '貼り付け' },
      { type: 'separator' }, { role: 'selectAll', label: 'すべて選択' });
  } else if (params.selectionText && params.selectionText.trim()) {
    t.push({ role: 'copy', label: 'コピー' },
      { label: `「${params.selectionText.trim().slice(0, 20)}」を辞書で調べる（英辞郎）`,
        click: () => shell.openExternal('https://eow.alc.co.jp/search?q=' + encodeURIComponent(params.selectionText.trim())) });
  }
  if (t.length) t.push({ type: 'separator' });
  t.push({ label: '拡大', accelerator: 'Ctrl+Plus', click: () => zoom(1) },
    { label: '縮小', accelerator: 'Ctrl+-', click: () => zoom(-1) },
    { label: '元の大きさ', accelerator: 'Ctrl+0', click: () => zoom(0) });
  Menu.buildFromTemplate(t).popup({ window: win });
}

// ---------- zoom ----------
function zoom(dir) {
  const wc = win.webContents;
  const z = dir === 0 ? 0 : Math.max(-3, Math.min(4, wc.getZoomLevel() + dir * 0.5));
  wc.setZoomLevel(z); saveState();
}

let win = null;
function createWindow() {
  state = loadState();
  win = new BrowserWindow({
    ...initialBounds(),
    minWidth: 400,
    minHeight: 560,
    title: '聞き読みプレーヤー',
    icon: path.join(ROOT, 'icon-512.png'),
    autoHideMenuBar: true,
    backgroundColor: '#F3F5F9',
    show: false,
    webPreferences: { contextIsolation: true, sandbox: true, backgroundThrottling: false, preload: path.join(__dirname, 'preload.js') },
  });
  if (state.maximized) win.maximize();
  win.once('ready-to-show', () => win.show());
  win.loadURL('app://listen-read/index.html');
  win.webContents.on('did-finish-load', () => { if (state.zoom) win.webContents.setZoomLevel(state.zoom); thumbar(); });
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:/.test(url)) shell.openExternal(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', (e, url) => { if (!url.startsWith('app://')) { e.preventDefault(); if (/^https?:/.test(url)) shell.openExternal(url); } });
  win.webContents.on('context-menu', (_e, p) => contextMenu(p));
  win.webContents.on('zoom-changed', (_e, d) => zoom(d === 'in' ? 1 : -1));
  win.webContents.on('before-input-event', (e, i) => {
    if (i.type !== 'keyDown') return;
    if (i.control && !i.alt) {
      if (['+', '=', ';', 'Add'].includes(i.key)) { zoom(1); e.preventDefault(); }
      else if (['-', 'Subtract'].includes(i.key)) { zoom(-1); e.preventDefault(); }
      else if (i.key === '0') { zoom(0); e.preventDefault(); }
    } else if (i.key === 'F11') { win.setFullScreen(!win.isFullScreen()); e.preventDefault(); }
  });
  let t = null;
  const later = () => { clearTimeout(t); t = setTimeout(saveState, 400); };
  win.on('resize', later); win.on('move', later);
  win.on('close', saveState);
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  protocol.handle('app', async (req) => {
    let p = decodeURIComponent(new URL(req.url).pathname);
    if (p === '/' || p === '') p = '/index.html';
    const file = path.normalize(path.join(ROOT, p));
    if (!file.startsWith(ROOT)) return new Response('Forbidden', { status: 403 });
    try { return await net.fetch(pathToFileURL(file).toString()); }
    catch (e) { return new Response('Not found', { status: 404 }); }
  });
  createWindow();
});

app.on('second-instance', () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
app.on('window-all-closed', () => app.quit());
