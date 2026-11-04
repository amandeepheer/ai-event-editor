/* Read-only API inventory. Presence is NOT proof that an editing operation works.
 * Never create actions, effects, sequences, exports, transcripts or keyframes here.
 */
const methods = (object, names) => object == null ? null :
  Object.fromEntries(names.map(name => [name, typeof object[name] === 'function']));

async function inspectCapabilities(ppro) {
  const report = {report_version:1, scope:'API presence only; no editing operations tested',
    host_editing_verified:false, project_open:false, sequence_open:false,
    sample_scope:'First clip found in up to 16 tracks per media type; up to 16 components and 32 parameters each. Not a whole-project audit.',
    errors:[], apis:{}, catalogs:{}, samples:{video:null,audio:null}};
  async function read(label, operation) {
    try { return await operation(); }
    catch (error) { report.errors.push('Could not inspect '+label+'. Retry with a stable open project.'); return null; }
  }
  async function catalog(label, factory, method) {
    if (!factory || typeof factory[method] !== 'function') return {status:'unavailable',match_names:[]};
    const values = await read(label, () => factory[method]());
    if (!Array.isArray(values) || values.some(v => typeof v !== 'string')) {
      return {status:'unreadable',match_names:[]};
    }
    return {status:'read',match_names:[...new Set(values)].sort()};
  }
  report.apis.video_effects = methods(ppro.VideoFilterFactory,['getMatchNames','createComponent']);
  report.apis.transitions = methods(ppro.TransitionFactory,['getVideoTransitionMatchNames','createVideoTransition']);
  report.apis.transcript = methods(ppro.Transcript,['hasTranscript','querySupportedLanguages','transcribeClipProjectItem','exportToJSON']);
  report.apis.text_value = {MogrtText:typeof ppro.MogrtText === 'function'};
  report.catalogs.video_effects = await catalog('video effect catalog',ppro.VideoFilterFactory,'getMatchNames');
  report.catalogs.transitions = await catalog('video transition catalog',ppro.TransitionFactory,'getVideoTransitionMatchNames');
  const manager = await read('export manager', () => ppro.EncoderManager &&
    typeof ppro.EncoderManager.getManager === 'function' ? ppro.EncoderManager.getManager() : null);
  report.apis.export = methods(manager,['exportSequence','launchEncoder']);
  const project = await read('active project', () => ppro.Project &&
    typeof ppro.Project.getActiveProject === 'function' ? ppro.Project.getActiveProject() : null);
  report.project_open = !!project;
  report.apis.project = methods(project,['createSequence','importFiles','executeTransaction','lockedAccess']);
  const sequence = await read('active sequence', () => project &&
    typeof project.getActiveSequence === 'function' ? project.getActiveSequence() : null);
  report.sequence_open = !!sequence;
  // No supported UXP Auto Reframe/speed setter/tracking command was found in
  // the audited Adobe declarations. Do not guess names or invoke legacy APIs.
  report.gaps = {
    auto_reframe:'No documented UXP command found. Adobe has an ExtendScript example; this plugin has no bridge. Use Sequence > Auto Reframe Sequence manually for now.',
    subject_tracking:'No dedicated documented UXP subject/mask tracking command found. Tracking controls remain manual.',
    retiming:'getSpeed reads speed; no documented direct speed setter or speed-ramp command found. Use Premiere Speed/Duration or Time Remapping manually.',
    captions:'Transcript access does not establish automatic caption-track creation. Captions remain manual.'
  };
  if (!sequence) return report;
  const settings = await read('sequence settings', () => typeof sequence.getSettings === 'function' ? sequence.getSettings() : null);
  report.apis.geometry = methods(settings,['setVideoFrameRect','setVideoPixelAspectRatio','setVideoFrameRate']);
  const editor = await read('sequence editor', () => ppro.SequenceEditor &&
    typeof ppro.SequenceEditor.getEditor === 'function' ? ppro.SequenceEditor.getEditor(sequence) : null);
  report.apis.timeline = methods(editor,['createInsertProjectItemAction','createOverwriteItemAction','createRemoveItemsAction','createCloneTrackItemAction','insertMogrtFromPath']);
  const clipType = ppro.Constants && ppro.Constants.TrackItemType && ppro.Constants.TrackItemType.CLIP;
  if (clipType === undefined) return report;
  for (const [kind,countMethod,trackMethod] of [['video','getVideoTrackCount','getVideoTrack'],['audio','getAudioTrackCount','getAudioTrack']]) {
    await read(kind+' clip sample', async () => {
      if (typeof sequence[countMethod] !== 'function' || typeof sequence[trackMethod] !== 'function') return;
      const count = await sequence[countMethod]();
      if (!Number.isInteger(count) || count < 0) throw new Error('Invalid track count');
      for (let i=0; i<Math.min(count,16); i++) {
        const track = await sequence[trackMethod](i);
        if (!track || typeof track.getTrackItems !== 'function') continue;
        const items = await track.getTrackItems(clipType,false);
        if (!Array.isArray(items) || !items.length) continue;
        const clip = items[0];
        const sample = {track_index:i, methods:methods(clip,['createSetInPointAction','createSetOutPointAction','createMoveAction',
          'createAddVideoTransitionAction','getComponentChain','getSpeed']),chain:null,components:[]};
        report.samples[kind] = sample;
        const chain = typeof clip.getComponentChain === 'function' ? await clip.getComponentChain() : null;
        sample.chain = methods(chain,['createAppendComponentAction','getComponentAtIndex','getComponentCount']);
        if (!chain || typeof chain.getComponentCount !== 'function' || typeof chain.getComponentAtIndex !== 'function') return;
        const components = await chain.getComponentCount();
        if (!Number.isInteger(components) || components < 0) throw new Error('Invalid component count');
        for (let c=0; c<Math.min(components,16); c++) {
          const component = await chain.getComponentAtIndex(c);
          if (!component || typeof component.getParamCount !== 'function' || typeof component.getParam !== 'function') continue;
          const entry = {component_index:c,parameters:[]}; sample.components.push(entry);
          const params = await component.getParamCount();
          if (!Number.isInteger(params) || params < 0) throw new Error('Invalid parameter count');
          for (let p=0; p<Math.min(params,32); p++) {
            const param = await component.getParam(p);
            entry.parameters.push({parameter_index:p,methods:methods(param,['createKeyframe','createSetValueAction',
              'createSetTimeVaryingAction','createAddKeyframeAction','getValueAtTime','areKeyframesSupported'])});
          }
        }
        return;
      }
    });
  }
  return report;
}

function formatCapabilities(report) {
  const has = (object, name) => object && object[name] === true;
  const available = value => value ? 'API present; plugin implementation pending' : 'Not observed; open a sequence with clips and retry';
  const lines = ['Premiere native-control check',report.scope,
    'Project: '+(report.project_open?'open':'not open')+' · Sequence: '+(report.sequence_open?'open':'not open'),
    'New editable sequence: existing experimental adapter; installed-host editing still unverified.',
    'Effects: '+available(has(report.apis.video_effects,'createComponent')),
    'Video transitions: '+available(has(report.apis.transitions,'createVideoTransition')),
    'Vertical/square dimensions: '+available(has(report.apis.geometry,'setVideoFrameRect')),
    'MOGRT insertion: '+available(has(report.apis.timeline,'insertMogrtFromPath')),
    'Transcript access: '+available(has(report.apis.transcript,'exportToJSON')),
    'Export: '+available(has(report.apis.export,'exportSequence')),
    'Effect catalog: '+report.catalogs.video_effects.status+' ('+report.catalogs.video_effects.match_names.length+' match names)',
    'Video transition catalog: '+report.catalogs.transitions.status+' ('+report.catalogs.transitions.match_names.length+' match names)',
    'Auto Reframe: '+report.gaps.auto_reframe,
    'Tracking: '+report.gaps.subject_tracking,
    'Slow motion / speed ramps: '+report.gaps.retiming,
    'Captions: '+report.gaps.captions,
    'Colour, motion and audio automation need per-effect parameter mapping and write/readback tests.',
    'No effects or timeline changes were applied. API presence is not an editing test.',...report.errors];
  return lines.join('\n');
}
module.exports = {inspectCapabilities,formatCapabilities};
