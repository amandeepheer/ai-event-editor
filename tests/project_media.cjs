const assert=require('node:assert/strict');
const {selectedProjectMedia,requireProject}=require('../premiere-plugin/project-media.js');
const mutate=()=>{throw new Error('Project media reader must not change the project');};
function media(path,options={}) {
  return {name:options.name||path, getId:()=>options.id||path,
    isSequence:async()=>!!options.sequence,isOffline:async()=>!!options.offline,
    isMergedClip:async()=>!!options.merged,isMulticamClip:async()=>!!options.multicam,
    getMediaFilePath:async()=>{if(options.fail)throw Error('offline');return path;},
    createSetInPointAction:mutate,createSetOutPointAction:mutate};
}
function folder(name,items){return {name,getId:()=>name,getItems:async()=>items};}
function host(selected) {
  const project={guid:{toString:()=> 'project-a'},getActiveSequence:mutate,importFiles:mutate,createSequence:mutate};
  const ppro={Project:{getActiveProject:async()=>project},ProjectUtils:{getSelection:async p=>{assert.equal(p,project);return {getItems:async()=>selected};}},
    FolderItem:{cast:item=>{if(!item.getItems)throw Error('not folder');return item;}},
    ClipProjectItem:{cast:item=>{if(!item.getMediaFilePath)throw Error('not source');return item;}}};
  return {ppro,project};
}
(async()=>{
  const video=media('C:/Event/A.MP4'),audio=media('C:/Event/music.wav');
  const nested=folder('nested',[audio,media('C:/event/a.mp4',{id:'other-project-reference'})]);
  const bin=folder('event',[video,nested,media('/missing.mp4',{offline:true}),media('/seq',{sequence:true}),
    media('/merged.mp4',{merged:true}),media('/multi.mp4',{multicam:true}),media('relative.mp4'),{name:'Graphics style'},media('/bad.mp4',{fail:true})]);
  const h=host([bin,video,nested]);
  const result=await selectedProjectMedia(h.ppro);
  assert.equal(result.projectId,'project-a');assert.deepEqual(result.files.map(f=>f.path),['C:/Event/A.MP4','C:/Event/music.wav']);
  assert.equal(result.skipped.length,7);
  assert(result.skipped.some(x=>x.includes('offline')));assert(result.skipped.some(x=>x.includes('sequences')));
  // No timeline, project import, source marks or edits are needed for collection.
  const empty=host([]);await assert.rejects(()=>selectedProjectMedia(empty.ppro),/Select videos/);
  empty.ppro.Project.getActiveProject=async()=>null;await assert.rejects(()=>selectedProjectMedia(empty.ppro),/Open a Premiere project/);
  await assert.rejects(()=>selectedProjectMedia({}),/selection APIs/);
  const switched=host([video]);let count=0;
  switched.ppro.Project.getActiveProject=async()=>++count===1?switched.project:{guid:{toString:()=> 'project-b'}};
  await assert.rejects(()=>selectedProjectMedia(switched.ppro),/project changed/);
  await assert.rejects(()=>requireProject(h.ppro,'project-b'),/project changed/);
  const many=host(Array.from({length:2001},(_,i)=>media('/'+i+'.mp4')));
  await assert.rejects(()=>selectedProjectMedia(many.ppro),/at most 2000/);
  let deep=media('/deep.mp4');for(let i=0;i<34;i++)deep=folder('bin'+i,[deep]);
  await assert.rejects(()=>selectedProjectMedia(host([deep]).ppro),/deeply nested/);
  const loop=[];const cycle=folder('cycle',loop);loop.push(cycle,video);
  assert.equal((await selectedProjectMedia(host([cycle]).ppro)).files.length,1);
  // Unix source paths retain case; Windows/UNC paths deduplicate case/slashes.
  const paths=host([media('/A.mp4'),media('/a.mp4'),media('\\\\server\\share\\B.mp4'),media('\\\\SERVER\\share\\b.mp4')]);
  assert.equal((await selectedProjectMedia(paths.ppro)).files.length,3);
  console.log('Project panel media selection passed (read-only Adobe API doubles, no timeline)');
})().catch(error=>{console.error(error);process.exit(1);});
