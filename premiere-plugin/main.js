/* Premiere-first local workflow. AI/planning logic lives in the Python engine. */
let onPanelShow=()=>{};
try {
  const {entrypoints}=require('uxp');
  entrypoints.setup({panels:{'ai-event-editor':{show(){onPanelShow();}}}});
} catch(error) { /* Explicit test DOM can run outside Adobe. */ }
const {EngineClient}=require('./engine.js');
const {validatePlan,preflightPlan}=require('./edit-plan.js');
const {applyNewSequence}=require('./premiere.js');
const $=id=>document.getElementById(id);
const client=new EngineClient();
const {AutoStart}=require('./autostart.js');
const uxp=require('uxp');
const automatic=new AutoStart({client,storage:uxp.storage.localFileSystem,shell:uxp.shell,platform:require('os').platform(),progress:message});
const state={paths:[],music:'',candidates:[],session:null,page:0,plan:null,busy:false,connected:false};
const pageSize=12;
function message(value){$('status').textContent=value;}
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
  const start=Number($('audio-start').value);
  const end=$('audio-end').value.trim()?Number($('audio-end').value):null;
  if(!Number.isFinite(start)||start<0||(end!==null&&(!Number.isFinite(end)||end<=start)))throw new Error('Choose a valid music excerpt.');
  return {duration:selectedDuration(),style:$('style').value,pacing:$('pacing').value,music:state.music,audio_start:start,audio_end:end};
}
function review(){return state.candidates.map(c=>({id:c.id,decision:c.decision,category:c.category}));}
function payload(){if(!state.session)throw new Error('Prepare your footage before building an edit.');return {session_id:state.session,setup:setup(),review:review(),instruction:$('instruction').value};}
function applyCapabilities(){
  if(client.health && client.health.vision_available===false){$('use-ai').checked=false;$('use-ai').disabled=true;$('analysis-hint').textContent='Basic review mode: GPU AI packages/models are not installed in this runtime.';}
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
function setPlan(plan){state.plan=validatePlan(plan);$('plan').value=JSON.stringify(state.plan,null,2);$('confirm-create').checked=false;$('edit-summary').textContent=state.plan.duration_seconds+' seconds · '+state.plan.segments.length+' editable video segments · '+state.plan.fps+' fps\n'+(state.plan.warnings||[]).join('\n');}
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
for(const id of ['duration-preset','style','pacing','use-ai'])$(id).addEventListener('change',()=>{if(id==='use-ai')state.session=null;invalidate();updateDuration();});
$('custom-seconds').addEventListener('input',updateDuration);updateDuration();
bind('configure-autostart',async()=>{
  const file=await uxp.storage.localFileSystem.getFileForOpening({types:['json'],allowMultiple:false});
  if(!file)return;
  await automatic.configure(file);state.connected=true;
  $('connection-status').textContent='Automatic startup is configured. The panel will connect when it opens.';
  message('Connected. You can prepare footage inside Premiere.');
});
onPanelShow=()=>perform(async()=>{
  try{if(await automatic.restore()){state.connected=true;$('connection-status').textContent='Connected automatically to your local engine.';message('Ready. Add footage or continue reviewing your edit.');}}
  catch(error){state.connected=false;$('connection-status').textContent='Automatic connection needs attention.';throw error;}
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
bind('clear-footage',async()=>{state.paths=[];state.candidates=[];state.session=null;state.page=0;invalidate();drawShots();$('footage-summary').textContent='No clips selected';});
bind('choose-music',async()=>{
  const file=await require('uxp').storage.localFileSystem.getFileForOpening({types:['wav','mp3','m4a','aac','flac'],allowMultiple:false});
  if(file){state.music=file.nativePath;$('music-summary').textContent=file.name;invalidate();}
});
bind('clear-music',async()=>{state.music='';$('music-summary').textContent='Music optional';$('audio-start').value='0';$('audio-end').value='';invalidate();});
bind('preview-music',async()=>{if(!state.music)throw new Error('Choose music first.');const s=setup();await previewSource(state.music,s.audio_start,s.audio_end===null?s.audio_start+s.duration:s.audio_end);});
bind('prepare',async()=>{
  if(!state.paths.length)throw new Error('Add footage first.');
  invalidate();
  const old=new Map(state.candidates.map(c=>[c.id,c]));
  const result=await client.operation('/v1/prepare',{paths:state.paths,use_ai:$('use-ai').checked},message);
  state.session=result.session_id;state.candidates=result.candidates;state.page=0;
  for(const c of state.candidates){if(old.has(c.id)){c.decision=old.get(c.id).decision;c.category=old.get(c.id).category;}}
  drawShots();message(result.analysis+'\n'+(result.errors.length?result.errors.join('\n'):'Moments ready for review.'));
});
bind('previous',async()=>{state.page=Math.max(0,state.page-1);drawShots();});
bind('next',async()=>{state.page++;drawShots();});
bind('interpret',async()=>{const result=await client.request('/v1/interpret',payload());adopt(result);message(result.unsupported.length?'Revise unsupported instructions before building.':'Instruction changes are shown above. Build when your review is ready.');});
bind('build',async()=>{
  invalidate();const result=await client.operation('/v1/build',payload(),message);
  setPlan(result.plan);$('instruction-result').textContent=result.instructions.applied.join('\n')||'Using your reviewed setup.';
  message('Edit ready. Review the summary and confirm creation of a new Premiere sequence.');
});
bind('create-sequence',async()=>{
  if(!$('confirm-create').checked)throw new Error('Confirm creation of a new sequence first.');
  if(!state.plan)throw new Error('Build or open an edit first.');
  try{const result=await applyNewSequence(require("premierepro"),state.plan,message);message('Created '+result.name+' with '+result.clips+' editable clips. Continue editing and export with Premiere’s normal tools.');}
  finally{$('confirm-create').checked=false;}
});
bind('inspect',async()=>{const premiere=require("premierepro");const project=await premiere.Project.getActiveProject();if(!project)throw new Error('Open a Premiere project first.');const sequence=await project.getActiveSequence();message(sequence?'Active sequence: '+sequence.name:'Premiere connected. No active sequence.');});
bind('save-plan',async()=>{if(!state.plan)throw new Error('Build or open an edit first.');const file=await require('uxp').storage.localFileSystem.getFileForSaving('reviewed-edit.json',{types:['json']});if(file){await file.write(JSON.stringify(state.plan,null,2));message('Edit saved.');}});
bind('open-plan',async()=>{const file=await require('uxp').storage.localFileSystem.getFileForOpening({types:['json'],allowMultiple:false});if(file){setPlan(JSON.parse(await file.read()));message('Saved edit opened. Review before creating a sequence.');}});
bind('toggle-plan',async()=>{$('plan-tools').hidden=!$('plan-tools').hidden;});
bind('validate',async()=>{const plan=validatePlan($('plan').value);const report=preflightPlan(plan);setPlan(plan);message('Validated '+report.clips+' clips · '+report.duration_seconds+' seconds. No timeline edits applied.');});
$('plan').addEventListener('input',()=>{state.plan=null;$('confirm-create').checked=false;});
if(typeof module!=='undefined')module.exports={state,client,automatic,onPanelShow,selectedDuration,setup,payload,drawShots,previewSource};

// Some UXP hosts deliver the first show during setup; cover that initial load too.
setTimeout(()=>onPanelShow(),0);
