// 聞き読みプレーヤー for Windows: serves the web app + bundled audio from app://listen-read/
const { app, BrowserWindow, protocol, net, shell, Menu } = require('electron');
const path = require('path');
const { pathToFileURL } = require('url');

protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true, corsEnabled: true } },
]);

const ROOT = app.isPackaged ? path.join(process.resourcesPath, 'web') : path.join(__dirname, 'web');

if (!app.requestSingleInstanceLock()) app.quit();

let win = null;
function createWindow() {
  win = new BrowserWindow({
    width: 560,
    height: 920,
    minWidth: 380,
    title: '聞き読みプレーヤー',
    icon: path.join(ROOT, 'icon-512.png'),
    autoHideMenuBar: true,
    backgroundColor: '#F3F5F9',
    webPreferences: { contextIsolation: true, sandbox: true, backgroundThrottling: false },
  });
  win.loadURL('app://listen-read/index.html');
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
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
