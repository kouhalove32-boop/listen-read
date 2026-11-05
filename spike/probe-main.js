const { app, BrowserWindow } = require('electron');
app.whenReady().then(async () => {
  const w = new BrowserWindow({ show: false });
  await w.loadURL('data:text/html,<p>probe</p>');
  const r = await w.webContents.executeJavaScript(`new Promise(res=>{
    const s=speechSynthesis; let n=0;
    const done=()=>res(s.getVoices().map(v=>({name:v.name,lang:v.lang,local:v.localService,def:v.default})));
    s.onvoiceschanged=()=>{ if(s.getVoices().length) done() };
    const iv=setInterval(()=>{ if(s.getVoices().length||++n>25){clearInterval(iv);done()} },200);
  })`);
  console.log('ELECTRON_VOICES ' + JSON.stringify(r));
  app.quit();
});
