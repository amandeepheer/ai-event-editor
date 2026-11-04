const assert=require('node:assert/strict');
const {EngineClient}=require('../premiere-plugin/engine.js');
const {AutoStart}=require('../premiere-plugin/autostart.js');
(async()=>{
  for(const base of ['https://example.com','http://localhost:8765','http://127.0.0.1:11434','http://127.0.0.1:8765@evil.example','http://127.0.0.1:8765/'])
    assert.throws(()=>new EngineClient({base}),/Engine must use/);
  let calls=0,launches=0;
  const client=new EngineClient({fetcher:async()=>{calls++;throw Error('Permission denied to the url http://127.0.0.1:8765/v1/health. Manifest entry not found.');}});
  await assert.rejects(()=>client.connect('private-token'),e=>e.preventLaunch && e.message.includes('network permission') && !e.message.includes('private-token'));
  const manager=new AutoStart({client,shell:{openPath:async()=>{launches++;return '';}},storage:{},platform:'win32',delay:async()=>{}});
  await assert.rejects(()=>manager.connectOrStart({token:'private-token'}),/network permission/);
  assert.equal(launches,0);assert.equal(calls,2); // Permission failure is never retried as helper startup.
  client.base='http://example.com';
  await assert.rejects(()=>client.request('/v1/health'),/Engine must use/);assert.equal(calls,2);
  const transient=new EngineClient({fetcher:async()=>{throw Error('Connection refused');}});
  await assert.rejects(()=>transient.connect('token'),e=>!e.preventLaunch);
  const good=new EngineClient({fetcher:async(url,options)=>{
    assert.equal(url,'http://127.0.0.1:8765/v1/health');
    assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');
    return {ok:true,json:async()=>({api_version:1,engine:'AI Event Editor',ffmpeg:true,ffprobe:true})};
  }});
  await good.connect('token');
  await assert.rejects(()=>good.request('https://example.com'),/Invalid engine endpoint/);
  console.log('Network permission error and fixed loopback destination checks passed; Adobe permission matching needs host verification.');
})().catch(e=>{console.error(e);process.exit(1);});
