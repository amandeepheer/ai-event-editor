/* Non-destructive Premiere UXP panel MVP. No timeline mutations yet. */
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
function validatePlan(value) {
  const plan = JSON.parse(value);
  if (!plan || !Array.isArray(plan.segments) || !plan.segments.length || !(plan.fps > 0)) {
    throw new Error("Plan must include positive fps and nonempty segments");
  }
  for (const segment of plan.segments) {
    if (typeof segment.path !== "string" || !segment.path ||
        !Number.isInteger(segment.duration_frames) || segment.duration_frames <= 0 ||
        !Number.isInteger(segment.timeline_start) || segment.timeline_start < 0) {
      throw new Error("Invalid segment in edit plan");
    }
  }
  return plan;
}
document.getElementById("validate").addEventListener("click", () => {
  try {
    const plan = validatePlan(document.getElementById("plan").value);
    message("Validated " + plan.segments.length + " clips at " + plan.fps +
            " fps. This is a preview only; no Premiere edits applied.");
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
