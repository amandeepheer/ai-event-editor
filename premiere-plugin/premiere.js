/* Adobe UXP 26.3+ integration. Native host verification is still required.
 * Only newly created sequence/subclips are edited. Original source marks and
 * existing sequences are never modified. No automatic save or delete calls.
 */
const {validatePlan} = require('./edit-plan.js');
function transaction(project, label, callback) {
  let success = false;
  project.lockedAccess(() => { success = project.executeTransaction(callback, label); });
  if (!success) throw new Error('Premiere rejected transaction: ' + label);
}
async function children(ppro, item) {
  try { return await ppro.FolderItem.cast(item).getItems(); }
  catch (error) { return []; }
}
async function findNamed(ppro, root, name) {
  for (const item of await children(ppro, root)) {
    if (item.name === name) return item;
    const found = await findNamed(ppro, item, name);
    if (found) return found;
  }
  return null;
}
function checkedPlan(value) {
  const plan = validatePlan(value);
  if (plan.segments.some(s => s.speed !== 1 || s.speed_effect.kind !== 'normal')) {
    throw new Error('Native speed effects are not implemented. Choose a normal-speed reviewed edit.');
  }
  if (plan.titles && plan.titles.length) throw new Error('Native titles are not implemented; remove title metadata before applying.');
  for (const s of plan.segments) {
    if (!/^([a-z]:[\\/]|\/|\\\\)/i.test(s.path)) throw new Error('Premiere needs absolute local source paths.');
  }
  if (plan.audio) {
    const a = plan.audio;
    if (!a || typeof a.path !== 'string' || !/^([a-z]:[\\/]|\/|\\\\)/i.test(a.path) ||
        typeof a.start_seconds !== 'number' || !Number.isFinite(a.start_seconds) || a.start_seconds < 0 ||
        a.duration_seconds !== plan.duration_seconds) throw new Error('Invalid music excerpt in plan.');
  }
  return plan;
}
async function applyNewSequence(ppro, value, progress = () => {}) {
  const plan = checkedPlan(value);
  if (!ppro.Project || !ppro.ClipProjectItem || !ppro.FolderItem || !ppro.SequenceEditor ||
      !ppro.TickTime || !ppro.FrameRate) throw new Error('Premiere UXP APIs unavailable. Premiere 26.3+ required.');
  const project = await ppro.Project.getActiveProject();
  if (!project) throw new Error('Open a Premiere project first.');
  const root = await project.getRootItem();
  const token = Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
  const binName = 'AI Event Editor ' + token;
  transaction(project, 'Create AI Event Editor media bin', action => {
    action.addAction(root.createBinAction(binName, true));
  });
  const binItem = await findNamed(ppro, root, binName);
  if (!binItem) throw new Error('Could not locate the new media bin. Existing sequences remain unchanged.');
  const paths = [...new Set(plan.segments.map(s => s.path).concat(plan.audio ? [plan.audio.path] : []))];
  progress('Importing local media…');
  if (!await project.importFiles(paths, true, binItem, false)) throw new Error('Media import failed. Check missing files and supported codecs.');
  const media = new Map();
  for (const item of await children(ppro, binItem)) {
    try {
      const clip = ppro.ClipProjectItem.cast(item);
      const path = await clip.getMediaFilePath();
      media.set(path.replace(/\\/g, '/').toLowerCase(), clip);
    } catch (error) { /* A folder or unsupported project item is not usable media. */ }
  }
  const jobs = plan.segments.map((s, i) => ({path:s.path, start:s.source_in_seconds,
    duration:s.duration_frames/plan.fps, time:s.timeline_start/plan.fps,
    name:token+'-'+String(i+1).padStart(5,'0'), video:true}));
  if (plan.audio) jobs.push({path:plan.audio.path, start:plan.audio.start_seconds,
    duration:plan.duration_seconds, time:0, name:token+'-music', video:false});
  // Resolve every source and check API support before creating any subclips.
  for (const job of jobs) {
    job.source = media.get(job.path.replace(/\\/g,'/').toLowerCase());
    if (!job.source) throw new Error('Imported source not found: '+job.path);
    if (typeof job.source.createSubClipAction !== 'function') throw new Error('Trimmed subclips require Premiere 26.3 or newer.');
  }
  transaction(project, 'Create reviewed source subclips', compound => {
    for (const job of jobs) compound.addAction(job.source.createSubClipAction(job.name,
      ppro.TickTime.createWithSeconds(job.start), ppro.TickTime.createWithSeconds(job.start+job.duration),
      true, {takeVideo:job.video, takeAudio:!job.video}));
  });
  for (const job of jobs) {
    job.item = await findNamed(ppro, root, job.name);
    if (!job.item) throw new Error('Could not resolve reviewed subclip: '+job.name);
  }
  let sequence;
  try {
    progress('Creating a new editable sequence…');
    sequence = await project.createSequence('AI Event Highlight '+token);
    if (!sequence || (await sequence.getEndTime()).seconds !== 0) throw new Error('Premiere did not return a new empty sequence.');
    const settings = await sequence.getSettings();
    if (typeof settings.setVideoFrameRate !== 'function' || !await settings.setVideoFrameRate(ppro.FrameRate.createWithValue(plan.fps))) {
      throw new Error('Premiere could not set the planned frame rate.');
    }
    transaction(project, 'Set AI highlight frame rate', compound => compound.addAction(sequence.createSetSettingsAction(settings)));
    const editor = ppro.SequenceEditor.getEditor(sequence);
    transaction(project, 'Apply reviewed AI Event edit', compound => {
      for (const job of jobs) compound.addAction(editor.createOverwriteItemAction(job.item,
        ppro.TickTime.createWithSeconds(job.time), 0, 0));
    });
    const actual = await sequence.getEndTime();
    if (Math.abs(actual.seconds-plan.duration_seconds) > 1/plan.fps+.000001) {
      throw new Error('Created duration does not match the plan; review the new sequence.');
    }
    if (!await project.openSequence(sequence)) throw new Error('Sequence created but Premiere could not open it.');
    return {name:sequence.name, clips:plan.segments.length, duration:plan.duration_seconds};
  } catch (error) {
    throw new Error(error.message + (sequence ? ' A new, possibly partial sequence was retained for review: '+sequence.name : '') + ' Existing sequences were not edited.');
  }
}
module.exports = {applyNewSequence, checkedPlan};
