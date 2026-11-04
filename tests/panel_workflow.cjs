/* Explicit DOM/UXP test double. This verifies events, not Adobe UI rendering. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
class Element{
  constructor(tag='div'){this.tagName=tag;this.children=[];this.handlers={};this.value='';this.checked=false;this.disabled=false;this.hidden=false;this.textContent='';}
  addEventListener(name,fn){(this.handlers[name] ||= []).push(fn);}
  async fire(name){for(const fn of this.handlers[name]||[])await fn({target:this});}
  appendChild(child){this.children.push(child);return child;}
  removeChild(child){this.children.splice(this.children.indexOf(child),1);}
  get firstChild(){return this.children[0];}
  setAttribute(name,value){this[name]=value;}
}
const html=fs.readFileSync(require('node:path').join(__dirname,'../premiere-plugin/index.html'),'utf8');
const elements={};
for(const match of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g))elements[match[2]]=new Element(match[1]);
const all=()=>{const result=[];const add=e=>{result.push(e);e.children.forEach(add);};Object.values(elements).forEach(add);return result;};
global.document={getElementById:id=>{assert(elements[id],'Missing HTML element: '+id);return elements[id];},
  createElement:tag=>new Element(tag),querySelectorAll:()=>all().filter(e=>['button','input','select','textarea'].includes(e.tagName))};
elements['duration-preset'].value='60';elements['custom-seconds'].value='90';elements['audio-start'].value='0';elements.style.value='energetic-event';elements.pacing.value='Balanced';
const requests=[];let currentPlan=null;let buildFailure=false;let version=1;let projectId='project-a';let projectAudioCount=2;
const candidates=Array.from({length:14},(_,i)=>({id:String(i),path:'C:/event'+i+'.mp4',start:0,end:4,category:'performance',quality:.5,decision:'keep',model:'manual-review',thumbnail_data:'data:image/png;base64,AA=='}));
function makePlan(){return {schema_version:1,fps:25,duration_frames:750,segments:[{path:'C:/event1.mp4',timeline_start:0,duration_frames:750,source_in_seconds:0}]};}
global.fetch=async(url,options)=>{
  assert(url.startsWith('http://127.0.0.1:8765/v1/'));
  assert.equal(options.headers.Authorization,'Bearer paired-secret');assert.equal(options.credentials,'omit');assert.equal(options.redirect,'error');
  const path=url.split('/v1/')[1];const body=options.body?JSON.parse(options.body):null;requests.push({path,body});
  let status=200,result;
  if(path==='health')result={engine:'AI Event Editor',api_version:version,ffmpeg:true,ffprobe:true,project_media_available:true};
  if(path==='prepare')result={job_id:'a'.repeat(32)};
  if(path==='project-media')result={job_id:'c'.repeat(32)};
  if(path==='jobs/'+'c'.repeat(32))result={status:'completed',result:{videos:[{path:'C:/event1.mp4',name:'event1.mp4'}],audio:Array.from({length:projectAudioCount},(_,i)=>({path:'C:/music'+i+'.wav',name:'music'+i+'.wav'})),errors:[]}};
  if(path==='jobs/'+'a'.repeat(32))result={status:'completed',result:{session_id:'review',candidates:JSON.parse(JSON.stringify(candidates)),errors:[],analysis:'Unranked'}};
  if(path==='interpret')result={setup:{...body.setup,duration:30,pacing:'Energetic'},candidates:body.review,applied:['Pacing: Energetic'],unsupported:[]};
  if(path==='build'){if(buildFailure){status=400;result={error:'Slow motion is not implemented yet'};}else{currentPlan=makePlan();result={job_id:'b'.repeat(32)};}}
  if(path==='jobs/'+'b'.repeat(32))result={status:'completed',result:{plan:currentPlan,instructions:{applied:['Length: 30 seconds']}}};
  assert(result,'Unknown mock endpoint '+path);return {ok:status<400,status,json:async()=>result};
};
const pickers=[];const saved=[];const previews=[];
const uxp={entrypoints:{setup(){}},storage:{localFileSystem:{getFileForOpening:async()=>pickers.shift(),getFileForSaving:async()=>({write:async text=>saved.push(text)})}}};
const projectSource=path=>({name:path,getMediaFilePath:async()=>path,isOffline:async()=>false,isSequence:async()=>false,isMergedClip:async()=>false,isMulticamClip:async()=>false});
const selection=[projectSource('C:/event1.mp4'),projectSource('C:/music0.wav'),projectSource('C:/music1.wav')];
const ppro={Project:{getActiveProject:async()=>({guid:{toString:()=>projectId},getActiveSequence:async()=>({name:'Existing client edit'})})},
  ProjectUtils:{getSelection:async()=>({getItems:async()=>selection})},
  FolderItem:{cast:()=>{throw Error('not a bin');}},ClipProjectItem:{cast:item=>item},
  SourceMonitor:{openFilePath:async path=>{previews.push(path);return true;},setPosition:async time=>{previews.push(time.seconds);return true;}},TickTime:{createWithSeconds:seconds=>({seconds})}};
const Module=require('node:module');const original=Module._load;
Module._load=function(name,parent,isMain){if(name==='uxp')return uxp;if(name==='premierepro')return ppro;return original.call(this,name,parent,isMain);};
const panel=require('../premiere-plugin/main.js');
const click=id=>elements[id].fire('click');
(async()=>{
  await click('step-review');assert.equal(elements['screen-review'].hidden,false);assert.equal(elements['screen-setup'].hidden,true);
  await click('step-setup');assert.equal(elements['screen-setup'].hidden,false);
  await click('toggle-connection');await click('toggle-utilities');
  elements['pairing-code'].value='paired-secret';await click('connect');assert(panel.state.connected);
  pickers.push([{nativePath:'C:/event1.mp4',name:'event1.mp4'}]);await click('add-footage');
  assert.deepEqual(panel.state.paths,['C:/event1.mp4']);
  pickers.push({nativePath:'C:/music.wav',name:'music.wav'});await click('choose-music');assert.equal(panel.state.music,'C:/music.wav');
  await click('prepare');assert.equal(elements['screen-review'].hidden,false);assert.equal(panel.state.candidates.length,14);assert.equal(elements.shots.children.length,12);
  const card=elements.shots.children[0];await card.children[1].children[1].fire('click');assert.equal(panel.state.candidates[0].decision,'reject');
  await click('next');assert.equal(elements.shots.children.length,2);
  await elements.shots.children[1].children[1].children[2].fire('click');assert.equal(panel.state.candidates[13].decision,'must_include');
  await elements.shots.children[0].children[1].children[3].fire('click');assert.deepEqual(previews,['C:/event12.mp4',0]);
  elements.instruction.value='Make a 30-second energetic recap';await elements.instruction.fire('input');await click('interpret');
  assert.equal(elements['duration-preset'].value,'30');assert.equal(elements.pacing.value,'Energetic');
  await click('build');assert(panel.state.plan);assert.equal(elements['screen-create'].hidden,false);assert(elements['edit-summary'].textContent.includes('1 source videos'));assert.equal(panel.state.plan.duration_frames,750);
  const sent=requests.find(r=>r.path==='build').body;
  assert.equal(sent.review[0].decision,'reject');assert.equal(sent.review[13].decision,'must_include');
  assert(sent.review.every(c=>Object.keys(c).sort().join(',')==='category,decision,id'));
  await click('save-plan');assert.equal(JSON.parse(saved[0]).duration_frames,750);
  elements.instruction.value='slow motion';await elements.instruction.fire('input');assert.equal(panel.state.plan,null);
  buildFailure=true;await click('build');assert(elements.status.textContent.includes('not implemented'));assert.equal(panel.state.plan,null);
  await click('create-sequence');assert(elements.status.textContent.includes('Confirm'));
  pickers.push({read:async()=>JSON.stringify(makePlan())});await click('open-plan');assert(panel.state.plan);
  await click('inspect');assert(elements.status.textContent.includes('Existing client edit'));
  const networkCalls=requests.length;
  await click('check-native-tools');
  assert(panel.state.capabilities.sequence_open);
  assert.equal(panel.state.capabilities.host_editing_verified,false);
  assert(elements['native-report'].textContent.includes('No effects or timeline changes were applied'));
  assert.equal(requests.length,networkCalls); // No helper/network required for this check.
  await click('save-native-report');
  assert.equal(JSON.parse(saved[1]).scope,'API presence only; no editing operations tested');
  await click('clear-music');assert.equal(panel.state.music,'');
  await click('clear-footage');assert.equal(panel.state.candidates.length,0);assert.equal(panel.state.session,null);
  buildFailure=false;elements.instruction.value='Make a 30-second energetic highlight';
  await click('use-project-media');assert.equal(panel.state.projectId,'project-a');
  assert.deepEqual(panel.state.paths,['C:/event1.mp4']);assert.equal(panel.state.session,null);
  assert.equal(panel.state.musicPending,true);
  const preparesBefore=requests.filter(r=>r.path==='prepare').length;
  await click('build');assert(elements.status.textContent.includes('Choose one project audio'));
  assert.equal(requests.filter(r=>r.path==='prepare').length,preparesBefore);
  elements['project-music'].value='1';await elements['project-music'].fire('change');
  await click('build');assert(panel.state.plan);
  assert.equal(requests.filter(r=>r.path==='prepare').length,preparesBefore+1);
  assert.equal(requests.filter(r=>r.path==='build').at(-1).body.setup.music,'C:/music1.wav');
  projectId='project-b';await click('build');assert(elements.status.textContent.includes('project changed'));assert.equal(panel.state.plan,null);
  projectId='project-a';await click('clear-footage');await click('clear-music');
  // Build from a blank panel captures the Project panel selection without a file picker.
  projectAudioCount=1;await click('build');assert(panel.state.plan);assert.equal(panel.state.music,'C:/music0.wav');
  assert.equal(panel.state.musicPending,false);
  assert.equal(pickers.length,0);
  elements['duration-preset'].value='auto';assert.throws(()=>panel.selectedDuration(),/not available/);
  version=2;await click('connect');assert(elements.status.textContent.includes('Incompatible'));
  Module._load=original;
  console.log('Panel event workflow passed (explicit DOM and Adobe API test doubles)');
})().catch(error=>{console.error(error);process.exit(1);});
