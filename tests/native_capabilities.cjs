const assert=require('node:assert/strict');
const {inspectCapabilities,formatCapabilities}=require('../premiere-plugin/capabilities.js');
const mutation=()=>{throw new Error('Inspector attempted an editing operation');};
function host(){
  const parameter={createKeyframe:mutation,createSetValueAction:mutation,createSetTimeVaryingAction:mutation,
    createAddKeyframeAction:mutation,getValueAtTime:mutation,areKeyframesSupported:mutation};
  // Deliberately omit parameter values and text: this inventory must not read them.
  const component={getParamCount:()=>1,getParam:()=>parameter};
  const chain={createAppendComponentAction:mutation,getComponentCount:()=>1,getComponentAtIndex:()=>component};
  const clip={createSetInPointAction:mutation,createSetOutPointAction:mutation,createMoveAction:mutation,
    createAddVideoTransitionAction:mutation,getSpeed:mutation,getComponentChain:()=>chain};
  const track={getTrackItems:(type,empty)=>{assert.equal(type,1);assert.equal(empty,false);return [clip];}};
  const sequence={getSettings:()=>({setVideoFrameRect:mutation,setVideoPixelAspectRatio:mutation,setVideoFrameRate:mutation}),
    getVideoTrackCount:()=>1,getVideoTrack:()=>track,getAudioTrackCount:()=>1,getAudioTrack:()=>track,
    autoReframeSequence:mutation}; // Even a stray legacy-looking member must not be invoked.
  const project={getActiveSequence:()=>sequence,createSequence:mutation,importFiles:mutation,
    executeTransaction:mutation,lockedAccess:mutation,save:mutation};
  const ppro={Project:{getActiveProject:()=>project},Constants:{TrackItemType:{CLIP:1}},
    VideoFilterFactory:{getMatchNames:()=>['PR.Effect B','PR.Effect A','PR.Effect A'],createComponent:mutation},
    TransitionFactory:{getVideoTransitionMatchNames:()=>['ADBE Cross Dissolve'],createVideoTransition:mutation},
    Transcript:{hasTranscript:mutation,querySupportedLanguages:mutation,transcribeClipProjectItem:mutation,exportToJSON:mutation},
    EncoderManager:{getManager:()=>({exportSequence:mutation,launchEncoder:mutation})},
    SequenceEditor:{getEditor:()=>({createInsertProjectItemAction:mutation,createOverwriteItemAction:mutation,
      createRemoveItemsAction:mutation,createCloneTrackItemAction:mutation,insertMogrtFromPath:mutation})}};
  return {ppro,project,sequence,track,component,parameter};
}
(async()=>{
  const h=host();const report=await inspectCapabilities(h.ppro);
  assert.equal(report.host_editing_verified,false);
  assert.equal(report.project_open,true);assert.equal(report.sequence_open,true);
  assert.equal(report.apis.geometry.setVideoFrameRect,true);
  assert.equal(report.apis.text_value.MogrtText,false); // Newer text API cannot be assumed on 26.3.
  assert.deepEqual(report.catalogs.video_effects.match_names,['PR.Effect A','PR.Effect B']);
  assert.equal(report.samples.video.chain.createAppendComponentAction,true);
  assert.equal(report.samples.audio.components[0].parameters[0].methods.createAddKeyframeAction,true);
  assert.deepEqual(report.errors,[]);
  assert(formatCapabilities(report).includes('plugin implementation pending'));
  assert(formatCapabilities(report).includes('No effects or timeline changes were applied'));
  // No project and partial API hosts still give useful catalogs without declaring support.
  h.ppro.Project.getActiveProject=()=>null;
  const empty=await inspectCapabilities(h.ppro);
  assert.equal(empty.project_open,false);assert.equal(empty.sequence_open,false);
  assert.equal(empty.samples.video,null);assert.equal(empty.apis.project,null);
  assert.equal(empty.catalogs.transitions.status,'read');
  const missing=await inspectCapabilities({});
  assert.equal(missing.catalogs.video_effects.status,'unavailable');
  assert(formatCapabilities(missing).includes('Not observed'));
  const broken=host();
  broken.ppro.VideoFilterFactory.getMatchNames=()=>{throw new Error('secret-path-must-not-be-exported');};
  broken.ppro.TransitionFactory.getVideoTransitionMatchNames=()=>[123];
  broken.sequence.getSettings=()=>{throw new Error('stale handle');};
  broken.sequence.getVideoTrack=()=>{throw new Error('stale track');};
  const partial=await inspectCapabilities(broken.ppro);
  assert.equal(partial.catalogs.video_effects.status,'unreadable');
  assert.equal(partial.catalogs.transitions.status,'unreadable');
  assert.equal(partial.apis.geometry,null);
  assert.equal(partial.errors.length,3);assert(partial.samples.audio);
  assert(!JSON.stringify(partial).includes('secret-path'));
  const bounded=host();let tracks=0,components=0,parameters=0;
  bounded.sequence.getVideoTrackCount=()=>1000;
  bounded.sequence.getVideoTrack=()=>{tracks++;return {getTrackItems:()=>[]};};
  bounded.component.getParamCount=()=>10000;
  bounded.component.getParam=()=>{parameters++;return bounded.parameter;};
  bounded.track.getTrackItems=()=>[{getComponentChain:()=>({
    getComponentCount:()=>1000,getComponentAtIndex:()=>{components++;return bounded.component;}})}];
  const limited=await inspectCapabilities(bounded.ppro);
  assert.equal(tracks,16);assert.equal(components,16);assert.equal(parameters,16*32);
  assert.equal(limited.samples.video,null);
  assert.equal(limited.samples.audio.components.length,16);
  console.log('Read-only native capability inventory passed (Adobe test doubles, not host editing verification)');
})().catch(error=>{console.error(error);process.exit(1);});
