/* Persist only a user-approved UXP file token, never a plaintext pairing secret. */
const configurationName='engine-connection.json';
const launcherName='Start-AI-Event-Engine.cmd';
const settingsName='engine-autostart.json';
function configuration(text,file){
  if(file.name!==configurationName)throw new Error('Select engine-connection.json created by Configure-Premiere-Autostart.cmd.');
  const data=JSON.parse(text);
  if(data.configuration_version!==1 || data.engine!=='AI Event Editor' || data.base!=='http://127.0.0.1:8765' ||
     data.launcher!==launcherName || typeof data.token!=='string' || !/^[a-zA-Z0-9_-]{32,128}$/.test(data.token)){
    throw new Error('Invalid automatic-start configuration. Run the configuration script again.');
  }
  const path=file.nativePath;
  if(typeof path!=='string'|| !/^[a-z]:[\\/]/i.test(path))throw new Error('Automatic helper launch currently requires a local Windows drive.');
  return {...data,launcherPath:path.replace(/[^\\/]+$/,launcherName)};
}
class AutoStart {
  constructor({client,storage,shell,platform,progress=()=>{},delay=ms=>new Promise(resolve=>setTimeout(resolve,ms))}){
    this.client=client;this.storage=storage;this.shell=shell;this.platform=platform;
    this.progress=progress;this.delay=delay;this.pending=null;
  }
  async settings(){
    if(!this.storage.getDataFolder)return null;
    const folder=await this.storage.getDataFolder();
    let entry;
    try{entry=await folder.getEntry(settingsName);}catch(error){return null;}
    const value=JSON.parse(await entry.read());
    if(!value || value.version!==1 || typeof value.fileToken!=='string')throw new Error('Saved automatic-start settings are invalid. Set up automatic start again.');
    return {folder,value};
  }
  async configure(file){
    if(this.platform!=='win32')throw new Error('Automatic helper startup is currently Windows-only. Manual connection remains available.');
    const config=configuration(await file.read(),file);
    await this.connectOrStart(config);
    const token=await this.storage.createPersistentToken(file);
    const folder=await this.storage.getDataFolder();
    const settings=await folder.createFile(settingsName,{overwrite:true});
    await settings.write(JSON.stringify({version:1,fileToken:token}));
    return true;
  }
  async restore(){
    const saved=await this.settings();
    if(!saved)return false;
    if(this.platform!=='win32')throw new Error('Saved automatic startup requires Windows.');
    let file;
    try{file=await this.storage.getEntryForPersistentToken(saved.value.fileToken);}
    catch(error){throw new Error('Automatic-start file moved or access expired. Set up automatic start again.');}
    const config=configuration(await file.read(),file);
    await this.connectOrStart(config);
    return true;
  }
  async connectOrStart(config){
    if(this.pending)return this.pending;
    this.pending=this.start(config);
    try{return await this.pending;}finally{this.pending=null;}
  }
  async start(config){
    this.progress('Connecting to your local engine…');
    try{return await this.client.connect(config.token);}
    catch(error){if(error.status || error.preventLaunch)throw error;}
    this.progress('Starting the local engine. Adobe may ask permission to launch it…');
    const result=await this.shell.openPath(config.launcherPath,'Start AI Event Editor’s local processing engine so you can edit inside Premiere. Your footage stays on this computer.');
    if(result!=='')throw new Error('Helper launch was declined or failed: '+result+'. Allow the Adobe launch request or start the helper manually.');
    for(let attempt=0;attempt<30;attempt++){
      await this.delay(1000);
      try{return await this.client.connect(config.token);}
      catch(error){if(error.status || error.preventLaunch)throw error;}
    }
    throw new Error('The helper did not become ready. Check Python, FFmpeg, project location and Windows script permissions, then set up automatic start again.');
  }
}
module.exports={AutoStart,configuration};
