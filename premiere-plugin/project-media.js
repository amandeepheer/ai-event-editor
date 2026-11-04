/* Read-only Project panel selection. Never reads or modifies a timeline. */
function projectKey(project) {
  if (!project || !project.guid || typeof project.guid.toString !== 'function')
    throw new Error('Premiere could not identify the active project. Reopen it and retry.');
  const key=project.guid.toString();
  if (!key || key==='[object Object]') throw new Error('Invalid Premiere project identity.');
  return key;
}
async function requireProject(ppro, expected) {
  const project=await ppro.Project.getActiveProject();
  if (!project) throw new Error('Open a Premiere project first.');
  if (expected && projectKey(project)!==expected)
    throw new Error('The active Premiere project changed. Select media in this project and use selected project media again.');
  return project;
}
async function selectedProjectMedia(ppro) {
  if (!ppro.Project || !ppro.ProjectUtils || typeof ppro.ProjectUtils.getSelection!=='function' ||
      !ppro.FolderItem || !ppro.ClipProjectItem)
    throw new Error('Project panel selection APIs are unavailable. Update Premiere or use the file picker.');
  const project=await requireProject(ppro), projectId=projectKey(project);
  const selection=await ppro.ProjectUtils.getSelection(project);
  const selected=selection && typeof selection.getItems==='function' ? await selection.getItems() : [];
  if (!Array.isArray(selected) || !selected.length)
    throw new Error('Select videos, audio files or bins in Premiere’s Project panel, then click Use selected project media. Nothing needs to be on a timeline.');
  const files=[], skipped=[], visited=new Set(), paths=new Set();
  let nodes=0;
  async function visit(item, depth) {
    if (++nodes>10000 || depth>32) throw new Error('Selection is too large or deeply nested. Select smaller bins.');
    let id=item;
    if (typeof item.getId==='function') {const value=item.getId();if(typeof value==='string'&&value)id=value;}
    if (visited.has(id)) return;
    visited.add(id);
    let folder;
    try { folder=ppro.FolderItem.cast(item); } catch (error) { /* Not a bin. */ }
    if (folder && typeof folder.getItems==='function') {
      const children=await folder.getItems();
      if (!Array.isArray(children)) throw new Error('Could not read the selected bin. Reopen the project and retry.');
      for (const child of children) await visit(child, depth+1);
      return;
    }
    const name=typeof item.name==='string' ? item.name : 'Project item';
    try {
      const clip=ppro.ClipProjectItem.cast(item);
      if (await clip.isSequence()) {skipped.push(name+': sequences are not source footage');return;}
      if (await clip.isOffline()) {skipped.push(name+': media is offline; relink it in Premiere');return;}
      if (await clip.isMergedClip() || await clip.isMulticamClip()) {
        skipped.push(name+': merged/multicam items are not supported; select original source clips');return;
      }
      const path=await clip.getMediaFilePath();
      if (typeof path!=='string' || !/^([a-z]:[\\/]|\/|\\\\)/i.test(path)) {
        skipped.push(name+': no absolute local media path');return;
      }
      const key=/^([a-z]:[\\/]|\\\\)/i.test(path) ? path.replace(/\\/g,'/').toLowerCase() : path;
      if (paths.has(key)) return;
      paths.add(key);files.push({path,name});
    } catch (error) {skipped.push(name+': not readable as local source media');}
    if (files.length>2000) throw new Error('Select at most 2000 local media files at once.');
  }
  for (const item of selected) await visit(item,0);
  await requireProject(ppro,projectId);
  if (!files.length) throw new Error('No usable local source files selected. '+skipped.slice(0,6).join('\n'));
  return {projectId,files,skipped};
}
module.exports={selectedProjectMedia,requireProject,projectKey};
