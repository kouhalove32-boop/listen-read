// Small bridge for Windows-only touches: taskbar progress, thumbnail buttons, version.
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('desktop', {
  isDesktop: true,
  version: ipcRenderer.sendSync('app-version'),
  state: (s) => ipcRenderer.send('player-state', { playing: !!s.playing, progress: Number(s.progress) || 0 }),
  onCommand: (cb) => ipcRenderer.on('player-command', (_e, c) => cb(c)),
});
