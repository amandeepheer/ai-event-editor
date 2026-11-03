/* Local edit-plan review and explicitly requested new-sequence creation. */
try {
  const { entrypoints } = require("uxp");
  entrypoints.setup({ panels: { "ai-event-editor": { show() {} } } });
} catch (error) { /* Allows Node-only validation tests outside Premiere. */ }
const status = document.getElementById("status");
const preset = document.getElementById("duration-preset");
const customSeconds = document.getElementById("custom-seconds");
const customPanel = document.getElementById("custom-duration");
const durationSummary = document.getElementById("duration-summary");
function selectedDuration() {
  if (preset.value === "auto") return null;
  const seconds = Number(preset.value === "custom" ? customSeconds.value : preset.value);
  if (!Number.isInteger(seconds) || seconds < 30 || seconds > 300) {
    throw new Error("Duration must be a whole number between 30 and 300 seconds");
  }
  return seconds;
}
function updateDuration() {
  customPanel.hidden = preset.value !== "custom";
  try {
    const seconds = selectedDuration();
    durationSummary.textContent = seconds === null ? "Auto duration: recommendation not yet implemented" :
      "Selected: " + Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
  } catch (error) { durationSummary.textContent = error.message; }
}
preset.addEventListener("change", updateDuration);
customSeconds.addEventListener("input", updateDuration);
updateDuration();

function message(value) { status.textContent = value; }
const { validatePlan, preflightPlan } = require("./edit-plan.js");
document.getElementById("validate").addEventListener("click", () => {
  try {
    const plan = validatePlan(document.getElementById("plan").value);
    const report = preflightPlan(plan);
    message("Validated " + report.clips + " clips · " + report.duration_seconds + " seconds at " + report.fps +
            " fps.\n" + (report.standalone_supported ? "Normal-speed standalone render supported." :
            "Standalone render blocked: unsupported speed effects on " + report.unsupported_speed_clips.join(", ")) +
            "\nValidation does not apply edits. Native sequence creation is experimental.");
  } catch (error) { message("Validation failed: " + error.message); }
});
document.getElementById("inspect").addEventListener("click", async () => {
  try {
    const premiere = require("premierepro");
    const project = await premiere.Project.getActiveProject();
    if (!project) { message("No active Premiere project. Open a project first."); return; }
    const sequence = await project.getActiveSequence();
    message(sequence ? "Connected to Premiere. Active sequence: " + sequence.name :
                      "Connected to Premiere. Open or create a sequence.");
  } catch (error) { message("Premiere connection unavailable: " + error.message); }
});
if (typeof module !== "undefined") module.exports = { validatePlan };

let applying = false;
document.getElementById("open-plan").addEventListener("click", async () => {
  if (applying) return;
  try {
    const fs = require("uxp").storage.localFileSystem;
    const file = await fs.getFileForOpening({types:["json"], allowMultiple:false});
    if (!file) return;
    const text = await file.read();
    const plan = validatePlan(text);
    document.getElementById("plan").value = text;
    document.getElementById("confirm-create").checked = false;
    message("Opened reviewed edit: " + plan.segments.length + " clips, " + plan.duration_seconds + " seconds. Review before creating a sequence.");
  } catch (error) { message("Could not open edit: " + error.message); }
});
document.getElementById("create-sequence").addEventListener("click", async () => {
  if (applying) return;
  if (!document.getElementById("confirm-create").checked) {
    message("Tick the confirmation to create a new sequence and import local media."); return;
  }
  try {
    const {applyNewSequence} = require("./premiere.js");
    const plan = validatePlan(document.getElementById("plan").value);
    applying = true;
    document.getElementById("create-sequence").disabled = true;
    const result = await applyNewSequence(require("premierepro"), plan, message);
    message("Created " + result.name + " with " + result.clips + " editable video clips. Review framing, timing and audio in Premiere before delivery.");
  } catch (error) { message("Sequence creation failed: " + error.message); }
  finally {
    applying = false;
    document.getElementById("create-sequence").disabled = false;
    document.getElementById("confirm-create").checked = false;
  }
});
