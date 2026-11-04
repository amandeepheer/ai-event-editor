const assert=require('node:assert/strict');
const {AutoStart,configuration}=require('../premiere-plugin/autostart.js');
const config={configuration_version:1,engine:'AI Event Editor',base:'http://127.0.0.1:8765',token:'t'.repeat(43),launcher:'Start-AI-Event-Engine.cmd'};
const file={name:'engine-connection.json',nativePath:'C:\\Users\\Aman\\AppData\\Local\\AIEventEditor\\engine-connection.json',read:async()=>JSON.stringify(config)};
function fixture({running=false,denied=false,auth=false,never=false}={}){
  const writes=[],launches=[];let online=running,stored=null;
  const client={connect:async token=>{assert.equal(token,config.token);if(auth){const e=Error('Pairing denied');e.status=401;throw e;}if(!online||never)throw new TypeError('Connection refused');return {api_version:1};}};
  const storage={getDataFolder:async()=>({getEntry:async()=>{if(!stored)throw Error('missing');return {read:async()=>stored};},createFile:async()=>({write:async text=>{stored=text;writes.push(JSON.parse(text));}})}),
    createPersistentToken:async entry=>{assert.equal(entry,file);return 'user-approved-file-token';},
    getEntryForPersistentToken:async token=>{assert.equal(token,'user-approved-file-token');return file;}};
  const shell={openPath:async(path,text)=>{launches.push({path,text});online=true;return denied?'User denied':'';}};
  const manager=new AutoStart({client,storage,shell,platform:'win32',delay:async()=>{}});
  return {manager,writes,launches,storage};
}
(async()=>{
  assert(configuration(JSON.stringify(config),file).launcherPath.endsWith('Start-AI-Event-Engine.cmd'));
  for(const patch of [{base:'https://evil.example'}, {launcher:'malicious.exe'}, {token:''}, {configuration_version:2}]){
    assert.throws(()=>configuration(JSON.stringify({...config,...patch}),file));
  }
  assert.throws(()=>configuration(JSON.stringify(config),{...file,name:'random.json'}));
  assert.throws(()=>configuration(JSON.stringify(config),{...file,nativePath:'relative.json'}));
  const first=fixture();assert.equal(await first.manager.restore(),false);
  await first.manager.configure(file);assert.equal(first.launches.length,1);
  assert(first.launches[0].text.includes('local processing engine'));
  assert.deepEqual(first.writes,[{version:1,fileToken:'user-approved-file-token'}]);
  assert(!JSON.stringify(first.writes).includes(config.token));
  await first.manager.restore();assert.equal(first.launches.length,1); // Running helper is reused.
  const reload=new AutoStart({client:first.manager.client,storage:first.storage,shell:first.manager.shell,platform:'win32',delay:async()=>{}});
  await reload.restore();assert.equal(first.launches.length,1); // New panel restores pairing, no copy/paste.
  const denied=fixture({denied:true});await assert.rejects(()=>denied.manager.configure(file),/declined/);assert.equal(denied.writes.length,0);
  const auth=fixture({auth:true});await assert.rejects(()=>auth.manager.configure(file),/Pairing denied/);assert.equal(auth.launches.length,0);
  const broken=fixture({never:true});await assert.rejects(()=>broken.manager.configure(file),/did not become ready/);assert.equal(broken.launches.length,1);
  const running=fixture({running:true});await Promise.all([running.manager.connectOrStart(config),running.manager.connectOrStart(config)]);assert.equal(running.launches.length,0);
  const duplicate=fixture();await Promise.all([duplicate.manager.connectOrStart(config),duplicate.manager.connectOrStart(config)]);assert.equal(duplicate.launches.length,1);
  const invalid=fixture();invalid.storage.getEntryForPersistentToken=async()=>{throw Error('missing');};await invalid.manager.configure(file);await assert.rejects(()=>invalid.manager.restore(),/moved or access expired/);
  const mac=fixture();mac.manager.platform='darwin';await assert.rejects(()=>mac.manager.configure(file),/Windows-only/);
  console.log('Automatic launch, remembered pairing, denial, timeout and duplicate-launch tests passed (mock UXP shell).');
})().catch(e=>{console.error(e);process.exit(1);});
