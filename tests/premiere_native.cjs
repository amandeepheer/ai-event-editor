const assert = require('node:assert/strict');
const {applyNewSequence} = require('../premiere-plugin/premiere.js');
function host(options={}) {
  const actions=[], imports=[], sequences=[], sourceMarks={untouched:true};
  let locked=false;
  const old={name:'Client edit', clips:[{manual:true}]};
  const root={name:'root',items:[], async getItems(){return this.items;},createBinAction(name){
    assert(locked); return ()=>this.items.push({name,items:[],getItems:async function(){return this.items;}});
  }};
  function source(path) {
    const item={name:path, getMediaFilePath:async()=>path, createSubClipAction(name,start,end,bounds,opts){
      assert(locked); assert(end.seconds>start.seconds); assert.equal(bounds,true);
      actions.push({name,start:start.seconds,end:end.seconds,opts});
      return ()=>root.items.push({name,duration:end.seconds-start.seconds,video:opts.takeVideo,audio:opts.takeAudio});
    }};
    if(options.oldHost) delete item.createSubClipAction;
    return item;
  }
  const project={
    getRootItem:async()=>root,
    lockedAccess(callback){assert(!locked);locked=true;try{callback();}finally{locked=false;}},
    executeTransaction(callback,label){assert(locked);const pending=[];callback({addAction:a=>pending.push(a)});
      if(options.failTransaction===label)return false;
      pending.forEach(a=>a());return true;},
    async importFiles(paths,suppress,bin,stills){
      imports.push({paths,suppress,bin,stills});if(options.failImport)return false;
      paths.forEach(p=>bin.items.push(source(p)));return true;
    },
    async createSequence(name){
      const sequence={name, clips:[], fps:null,getEndTime:async function(){return {seconds:Math.max(0,...this.clips.map(c=>c.time+c.item.duration))};},
        getSettings:async()=>({setVideoFrameRate:async rate=>{sequence.fps=rate.value;return true;}}),
        createSetSettingsAction(){assert(locked);return ()=>{};}};
      sequences.push(sequence);return sequence;
    },
    openSequence:async()=>true
  };
  const ppro={Project:{getActiveProject:async()=>options.noProject?null:project},
    ClipProjectItem:{cast:item=>{if(!item.getMediaFilePath)throw Error('not source');return item;}},
    FolderItem:{cast:item=>{if(!item.getItems)throw Error('not folder');return item;}},
    TickTime:{createWithSeconds:seconds=>({seconds})},FrameRate:{createWithValue:value=>({value})},
    SequenceEditor:{getEditor:sequence=>({createOverwriteItemAction(item,time,v,a){assert(locked);assert.equal(v,0);assert.equal(a,0);return ()=>sequence.clips.push({item,time:time.seconds});}})}
  };
  return {ppro, old, sequences, sourceMarks, actions, imports, root};
}
function plan() {
  return {schema_version:1,fps:25,duration_frames:50,segments:[
    {id:'a',path:'C:/Footage/event.mp4',timeline_start:0,duration_frames:25,source_in_seconds:5,source_fps:50},
    {id:'b',path:'C:/Footage/event.mp4',timeline_start:25,duration_frames:25,source_in_seconds:12,source_fps:50}],
    audio:{path:'C:/Music/song.wav',start_seconds:30,duration_seconds:2}};
}
(async()=>{
  const h=host();const original=JSON.stringify(h.old);const p=plan();const copy=JSON.stringify(p);
  const result=await applyNewSequence(h.ppro,p);
  assert.equal(result.clips,2);assert.equal(h.sequences.length,1);
  assert.equal(h.sequences[0].fps,25);assert.equal(h.sequences[0].clips.length,3);
  assert.deepEqual(h.actions.map(a=>[a.start,a.end]),[[5,6],[12,13],[30,32]]);
  assert.deepEqual(h.actions.map(a=>a.opts),[{takeVideo:true,takeAudio:false},{takeVideo:true,takeAudio:false},{takeVideo:false,takeAudio:true}]);
  assert.deepEqual(h.sequences[0].clips.map(c=>c.time),[0,1,0]);
  assert.equal(JSON.stringify(h.old),original);assert.deepEqual(h.sourceMarks,{untouched:true});
  assert.equal(JSON.stringify(p),copy);assert.equal(h.imports[0].paths.length,2);
  await applyNewSequence(h.ppro,plan());assert.equal(h.sequences.length,2);
  assert.notEqual(h.sequences[0].name,h.sequences[1].name);
  for(const bad of ['ramp','relative','title','audio']){
    const mock=host();const data=plan();
    if(bad==='ramp')data.segments[0].speed_effect={kind:'ramp',speed:1};
    if(bad==='relative')data.segments[0].path='relative.mp4';
    if(bad==='title')data.titles=[{text:'Hello'}];
    if(bad==='audio')data.audio.start_seconds=-1;
    await assert.rejects(()=>applyNewSequence(mock.ppro,data));assert.equal(mock.root.items.length,0);
  }
  for(const opts of [{noProject:true},{failImport:true},{oldHost:true},{failTransaction:'Apply reviewed AI Event edit'}]){
    const mock=host(opts);const old=JSON.stringify(mock.old);
    await assert.rejects(()=>applyNewSequence(mock.ppro,plan()));
    assert.equal(JSON.stringify(mock.old),old);
  }
  console.log('Native adapter contract tests passed (mock Adobe host; not Premiere runtime verification)');
})().catch(error=>{console.error(error);process.exit(1);});
