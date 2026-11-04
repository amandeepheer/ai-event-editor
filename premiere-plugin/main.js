/* Premiere-first local workflow. AI/planning logic lives in the Python engine. */
let onPanelShow=()=>{};
try {
  const {entrypoints}=require('uxp');
  entrypoints.setup({panels:{'ai-event-editor':{show(){onPanelShow();}}}});
} catch(error) { /* Explicit test DOM can run outside Adobe. */ }
const {EngineClient}=require('./engine.js');
const {validatePlan,preflightPlan}=require('./edit-plan.js');
const {applyNewSequence}=require('./premiere.js');
const {inspectCapabilities,formatCapabilities}=require('./capabilities.js');
const {selectedProjectMedia,requireProject}=require('./project-media.js');
const $=id=>document.getElementById(id);
const client=new EngineClient();
const {AutoStart}=require('./autostart.js');
const uxp=require('uxp');
const automatic=new AutoStart({client,storage:uxp.storage.localFileSystem,shell:uxp.shell,platform:require('os').platform(),progress:message});
const state={paths:[],music:'',candidates:[],session:null,page:0,plan:null,busy:false,connected:false,capabilities:null,projectId:null,projectAudio:[],musicPending:false};
const pageSize=12;
function message(value){$('status').textContent=value;}
function showStep(step){
  for(const name of ['setup','review','create']){
    $('screen-'+name).hidden=name!==step;
    $('step-'+name).setAttribute('aria-pressed',String(name===step));
  }
}
function invalidate(){state.plan=null;$('plan').value='';$('confirm-create').checked=false;$('edit-summary').textContent='Inputs changed. Build the reviewed edit again.';}
function selectedDuration(){
  if($('duration-preset').value==='auto')throw new Error('Choose a length from 30–300 seconds; automatic length is not available yet.');
  const seconds=Number($('duration-preset').value==='custom'?$('custom-seconds').value:$('duration-preset').value);
  if(!Number.isInteger(seconds)||seconds<30||seconds>300)throw new Error('Duration must be a whole number between 30 and 300 seconds');
  return seconds;
}
function updateDuration(){
  $('custom-duration').hidden=$('duration-preset').value!=='custom';
  try{const s=selectedDuration();$('duration-summary').textContent='Selected: '+Math.floor(s/60)+':'+String(s%60).padStart(2,'0');}
  catch(error){$('duration-summary').textContent=error.message;}
}
function setup(){
  if(state.musicPending)throw new Error('Choose one project audio file as music, or choose No music, before building.');
  const start=Number($('audio-start').value);
  const end=$('audio-end').value.trim()?Number($('audio-end').value):null;
  if(!Number.isFinite(start)||start<0||(end!==null&&(!Number.isFinite(end)||end<=start)))throw new Error('Choose a valid music excerpt.');
  return {duration:selectedDuration(),style:$('style').value,pacing:$('pacing').value,music:state.music,audio_start:start,audio_end:end};
}
function review(){return state.candidates.map(c=>({id:c.id,decision:c.decision,category:c.category}));}
function payload(){if(!state.session)throw new Error('Prepare your footage before building an edit.');return {session_id:state.session,setup:setup(),review:review(),instruction:$('instruction').value,instruction_mode:$('use-language-model').checked?'ollama':'rules'};}
function applyCapabilities(){
  if(client.health && client.health.vision_available===false){$('use-ai').checked=false;$('use-ai').disabled=true;$('analysis-hint').textContent='AI packages/model are not ready. Use Install CLIP in Setup and Status, then reconnect.';}
}
function lock(value){
  state.busy=value;
  for(const el of document.querySelectorAll('button,input,select,textarea'))el.disabled=value;
  if(!value)applyCapabilities();
}
async function perform(work){
  if(state.busy)return;
  lock(true);
  try{await work();}catch(error){message(error.message);}
  finally{lock(false);}
}
function bind(id,action){$(id).addEventListener('click',()=>perform(action));}
async function checkProject(){if(state.projectId)await requireProject(require("premierepro"),state.projectId);}
function projectMusicChoices(files){
  state.projectAudio=files;
  const select=$('project-music');while(select.firstChild)select.removeChild(select.firstChild);
  if(files.length>1){const option=document.createElement('option');option.value='pending';option.textContent='Choose music from selected project audio…';select.appendChild(option);}
  const none=document.createElement('option');none.value='';none.textContent='No music';select.appendChild(none);
  files.forEach((file,index)=>{const option=document.createElement('option');option.value=String(index);option.textContent=file.name;select.appendChild(option);});
  state.musicPending=files.length>1;
  select.value=files.length>1?'pending':files.length===1?'0':'';
  state.music=files.length===1?files[0].path:'';
  $('project-music-field').hidden=files.length===0;
  $('music-summary').textContent=state.musicPending?'Select one project audio file below':files.length===1?files[0].name:'Music optional';
  $('audio-start').value='0';$('audio-end').value='';
}
async function useProjectMedia(){
  if(!client.health)throw new Error('Connect the local engine first, then use selected project media.');
  if(!client.health.project_media_available)throw new Error('Update the plugin and local helper to version 0.5 or newer, stop the older helper, then reconnect to use Project panel media.');
  const result=await selectedProjectMedia(require("premierepro"));
  const media=await client.operation('/v1/project-media',{paths:result.files.map(f=>f.path)},message);
  await requireProject(require("premierepro"),result.projectId);
  if(!media.videos.length&&!media.audio.length)throw new Error('No readable video/audio found. '+media.errors.join('\n'));
  // Replace the pool explicitly; selection changes do not quietly expand an edit.
  state.paths=media.videos.map(f=>f.path);state.projectId=result.projectId;
  state.session=null;state.candidates=[];state.page=0;invalidate();drawShots();
  projectMusicChoices(media.audio);
  $('footage-summary').textContent=state.paths.length+' videos from the Project panel';
  const warnings=[...result.skipped,...media.errors];
  $('project-media-report').textContent=state.paths.length+' videos · '+media.audio.length+' audio files. Whole linked source files are used; source In/Out marks, subclip bounds and source effects are not copied.\n'+warnings.join('\n');
  message(state.paths.length?'Project media ready. Type supported instructions and build, or prepare/review moments first.':'Audio loaded. Select videos and audio together, or add footage with the file picker.');
}
async function prepareMoments(){
  if(!state.paths.length)throw new Error('Select videos or a bin in the Project panel and use selected project media, or add footage.');
  await checkProject();invalidate();
  const old=new Map(state.candidates.map(c=>[c.id,c]));
  const result=await client.operation('/v1/prepare',{paths:state.paths,use_ai:$('use-ai').checked},message);
  await checkProject();
  state.session=result.session_id;state.candidates=result.candidates;state.page=0;
  for(const c of state.candidates){if(old.has(c.id)){c.decision=old.get(c.id).decision;c.category=old.get(c.id).category;}}
  drawShots();
  showStep('review');
  if(result.errors.length)$('project-media-report').textContent+='\nPreparation issues:\n'+result.errors.join('\n');
  message(result.analysis+'\n'+(result.errors.length?result.errors.join('\n'):'Moments ready for review.'));
}
async function ensurePrepared(){
  if(!state.paths.length)await useProjectMedia();
  await checkProject();
  setup(); // Resolve ambiguous music choices before starting expensive analysis.
  if(!state.session)await prepareMoments();
}
function setPlan(plan){state.plan=validatePlan(plan);$('plan').value=JSON.stringify(state.plan,null,2);$('confirm-create').checked=false;const used=new Set(state.plan.segments.map(s=>s.path)).size;$('edit-summary').textContent=state.plan.duration_seconds+' seconds · '+state.plan.segments.length+' editable video segments · '+used+' source videos · '+state.plan.fps+' fps\n'+(state.plan.warnings||[]).join('\n');showStep('create');}
function adopt(result){
  const s=result.setup;
  if(['30','60','120','300'].includes(String(s.duration)))$('duration-preset').value=String(s.duration);
  else{$('duration-preset').value='custom';$('custom-seconds').value=String(s.duration);}
  $('style').value=s.style;$('pacing').value=s.pacing;updateDuration();
  const changes=new Map(result.candidates.map(c=>[c.id,c]));
  for(const c of state.candidates){const patch=changes.get(c.id);if(patch){c.decision=patch.decision;c.category=patch.category;}}
  $('instruction-result').textContent=(result.applied.length?result.applied.join('\n'):'No changes requested.')+
    (result.unsupported.length?'\nCannot apply:\n'+result.unsupported.join('\n'):'\nSupported instructions ready.');
  invalidate();drawShots();
}
function drawShots(){
  const kept=state.candidates.filter(c=>c.decision!=='reject');
  const pins=kept.filter(c=>c.decision==='must_include').length;
  $('review-summary').textContent=kept.length+' eligible moments · '+pins+' must include. Keep is eligible; Must include guarantees an excerpt when it fits.';
  const pages=Math.max(1,Math.ceil(state.candidates.length/pageSize));state.page=Math.min(state.page,pages-1);
  $('page-summary').textContent=state.candidates.length?'Page '+(state.page+1)+' / '+pages:'0 moments';
  const root=$('shots');while(root.firstChild)root.removeChild(root.firstChild);
  for(const candidate of state.candidates.slice(state.page*pageSize,(state.page+1)*pageSize)){
    const card=document.createElement('div');card.className='shot';
    const top=document.createElement('div');top.className='shot-top';
    if(candidate.thumbnail_data){const img=document.createElement('img');img.src=candidate.thumbnail_data;img.alt='Source moment thumbnail';top.appendChild(img);}
    const info=document.createElement('div');info.className='shot-info';
    const title=document.createElement('strong');title.textContent=candidate.path.split(/[\\/]/).pop();info.appendChild(title);
    const range=document.createElement('p');range.textContent=candidate.start.toFixed(2)+'–'+candidate.end.toFixed(2)+'s · '+(candidate.model==='manual-review'?'Unranked': 'Suggested category; review required');info.appendChild(range);top.appendChild(info);card.appendChild(top);
    const buttons=document.createElement('div');buttons.className='actions';
    for(const [label,decision] of [['Keep','keep'],['Reject','reject'],['Must include','must_include']]){
      const button=document.createElement('button');button.textContent=label;button.className='secondary'+(candidate.decision===decision?' chosen':'');
      button.addEventListener('click',()=>{if(state.busy)return;candidate.decision=decision;invalidate();drawShots();});buttons.appendChild(button);
    }
    const preview=document.createElement('button');preview.textContent='Preview in Premiere';preview.className='secondary';
    preview.addEventListener('click',()=>perform(()=>previewSource(candidate.path,candidate.start,candidate.end)));buttons.appendChild(preview);card.appendChild(buttons);
    const select=document.createElement('select');select.setAttribute('aria-label','Moment category');
    for(const name of ['drone','stalls','performance','dancing','crowd','finale']){const option=document.createElement('option');option.value=name;option.textContent=name;select.appendChild(option);}
    select.value=candidate.category;select.addEventListener('change',()=>{candidate.category=select.value;invalidate();});card.appendChild(select);
    if(candidate.warning){const warning=document.createElement('p');warning.textContent=candidate.warning;card.appendChild(warning);}
    root.appendChild(card);
  }
}
async function previewSource(path,start,end){
  const ppro=require("premierepro");
  if(!ppro.SourceMonitor||!ppro.SourceMonitor.openFilePath||!ppro.SourceMonitor.setPosition)throw new Error('Source Monitor preview requires Premiere 26.3+.');
  if(!await ppro.SourceMonitor.openFilePath(path))throw new Error('Premiere could not preview this source.');
  if(!await ppro.SourceMonitor.setPosition(ppro.TickTime.createWithSeconds(start)))throw new Error('Premiere could not seek to this moment.');
  message('Source Monitor opened at '+start.toFixed(2)+'s. Review until '+end.toFixed(2)+'s using Premiere playback controls.');
}
for(const id of ['audio-start','audio-end','custom-seconds','instruction'])$(id).addEventListener('input',invalidate);
for(const step of ['setup','review','create'])bind('step-'+step,async()=>showStep(step));
bind('toggle-connection',async()=>{$('connection-panel').hidden=!$('connection-panel').hidden;});
bind('toggle-utilities',async()=>{$('utilities').hidden=!$('utilities').hidden;});
for(const id of ['duration-preset','style','pacing','use-ai','use-language-model'])$(id).addEventListener('change',()=>{if(id==='use-ai')state.session=null;invalidate();updateDuration();});
$('custom-seconds').addEventListener('input',updateDuration);updateDuration();
bind('configure-autostart',async()=>{
  const file=await uxp.storage.localFileSystem.getFileForOpening({types:['json'],allowMultiple:false});
  if(!file)return;
  await automatic.configure(file);state.connected=true;
  $('connection-status').textContent='Automatic startup is configured. The panel will connect when it opens.';
  message('Connected. You can prepare footage inside Premiere.');
});
onPanelShow=()=>perform(async()=>{
  try{if(await automatic.restore()){state.connected=true;$('connection-status').textContent='Connected automatically to your local engine.';message('Ready. Add footage or continue reviewing your edit.');}else{$('connection-panel').hidden=state.connected;}}
  catch(error){state.connected=false;$('connection-panel').hidden=false;$('connection-status').textContent='Automatic connection needs attention.';throw error;}
});
bind('connect',async()=>{
  state.connected=false;$('connection-status').textContent='Connecting to the local helper…';
  let health;
  try{health=await client.connect($('pairing-code').value);}
  catch(error){$('connection-status').textContent='Disconnected. Check the helper and pairing code.';throw error;}
  state.connected=true;$('connection-status').textContent='Connected to your local engine. Footage stays on this computer.';
  message(health.busy?'Connected. The engine is finishing another job.':'Connected. Add footage and prepare your moments.');
});
bind('add-footage',async()=>{
  const files=await require('uxp').storage.localFileSystem.getFileForOpening({types:['mp4','mov','mxf','m4v'],allowMultiple:true});
  if(!files)return;for(const file of Array.isArray(files)?files:[files])if(!state.paths.includes(file.nativePath))state.paths.push(file.nativePath);
  $('footage-summary').textContent=state.paths.length+' local clips selected';state.session=null;invalidate();
});
bind('use-project-media',useProjectMedia);
bind('clear-footage',async()=>{state.paths=[];state.candidates=[];state.session=null;state.page=0;state.projectId=null;invalidate();drawShots();$('footage-summary').textContent='No clips selected';$('project-media-report').textContent='';});
bind('choose-music',async()=>{
  const file=await require('uxp').storage.localFileSystem.getFileForOpening({types:['wav','mp3','m4a','aac','flac'],allowMultiple:false});
  if(file){projectMusicChoices([]);state.music=file.nativePath;$('music-summary').textContent=file.name;invalidate();}
});
$('project-music').addEventListener('change',()=>{
  const value=$('project-music').value;state.musicPending=value==='pending';
  state.music=value!==''&&value!=='pending'?state.projectAudio[Number(value)].path:'';
  $('music-summary').textContent=state.musicPending?'Choose project music':state.music?state.projectAudio[Number(value)].name:'Music optional';
  $('audio-start').value='0';$('audio-end').value='';invalidate();
});
bind('clear-music',async()=>{projectMusicChoices([]);invalidate();});
bind('preview-music',async()=>{if(!state.music)throw new Error('Choose music first.');const s=setup();await previewSource(state.music,s.audio_start,s.audio_end===null?s.audio_start+s.duration:s.audio_end);});
bind('prepare',prepareMoments);
bind('previous',async()=>{state.page=Math.max(0,state.page-1);drawShots();});
bind('next',async()=>{state.page++;drawShots();});
bind('interpret',async()=>{await ensurePrepared();const body=payload();const result=body.instruction_mode==='ollama'?await client.operation('/v1/interpret-local',body,message):await client.request('/v1/interpret',body);await checkProject();adopt(result);showStep('setup');message(result.unsupported.length?'Revise unsupported instructions before building.':'Instruction changes are shown above. Continue to Review when ready.');});
bind('build',async()=>{
  invalidate();await ensurePrepared();const result=await client.operation('/v1/build',payload(),message);await checkProject();
  setPlan(result.plan);$('instruction-result').textContent=result.instructions.applied.join('\n')||'Using your reviewed setup.';
  message('Edit ready. Review the summary and confirm creation of a new Premiere sequence.');
});
bind('create-sequence',async()=>{
  if(!$('confirm-create').checked)throw new Error('Confirm creation of a new sequence first.');
  if(!state.plan)throw new Error('Build or open an edit first.');
  try{const result=await applyNewSequence(require("premierepro"),state.plan,message,{expectedProjectId:state.projectId});message('Created '+result.name+' with '+result.clips+' editable clips. Continue editing and export with Premiere’s normal tools.');}
  finally{$('confirm-create').checked=false;}
});
bind('inspect',async()=>{const premiere=require("premierepro");const project=await premiere.Project.getActiveProject();if(!project)throw new Error('Open a Premiere project first.');const sequence=await project.getActiveSequence();message(sequence?'Active sequence: '+sequence.name:'Premiere connected. No active sequence.');});
bind('check-native-tools',async()=>{
  state.capabilities=null;$('native-report').textContent='Reading Premiere APIs and installed effect/transition catalogs…';
  state.capabilities=await inspectCapabilities(require("premierepro"));
  $('native-report').textContent=formatCapabilities(state.capabilities);
  message('Native tool inventory ready. This check reads APIs; it does not test or apply edits.');
});
bind('save-native-report',async()=>{
  if(!state.capabilities)throw new Error('Check native tools first.');
  const file=await require('uxp').storage.localFileSystem.getFileForSaving('premiere-native-capabilities.json',{types:['json']});
  if(file){await file.write(JSON.stringify(state.capabilities,null,2));message('Native API inventory saved locally. No editing operations were tested.');}
});
bind('save-plan',async()=>{if(!state.plan)throw new Error('Build or open an edit first.');const file=await require('uxp').storage.localFileSystem.getFileForSaving('reviewed-edit.json',{types:['json']});if(file){await file.write(JSON.stringify(state.plan,null,2));message('Edit saved.');}});
bind('open-plan',async()=>{const file=await require('uxp').storage.localFileSystem.getFileForOpening({types:['json'],allowMultiple:false});if(file){setPlan(JSON.parse(await file.read()));message('Saved edit opened. Review before creating a sequence.');}});
bind('toggle-plan',async()=>{$('plan-tools').hidden=!$('plan-tools').hidden;});
bind('validate',async()=>{const plan=validatePlan($('plan').value);const report=preflightPlan(plan);setPlan(plan);message('Validated '+report.clips+' clips · '+report.duration_seconds+' seconds. No timeline edits applied.');});
$('plan').addEventListener('input',()=>{state.plan=null;$('confirm-create').checked=false;});
if(typeof module!=='undefined')module.exports={state,client,automatic,onPanelShow,selectedDuration,setup,payload,drawShots,previewSource};

// Some UXP hosts deliver the first show during setup; cover that initial load too.
setTimeout(()=>onPanelShow(),0);
