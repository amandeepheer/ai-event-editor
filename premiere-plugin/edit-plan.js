/* Local mirror of ai_event_editor.edit_plan; shared contract fixtures run in CI. */
function validatePlan(value) {
  const plan = typeof value === "string" ? JSON.parse(value) : JSON.parse(JSON.stringify(value));
  const object = x => x !== null && typeof x === "object" && !Array.isArray(x);
  const number = (x, label, positive = false, integer = false) => {
    if (typeof x !== "number" || !Number.isFinite(x) || x < 0 ||
        (positive && x <= 0) || (integer && !Number.isInteger(x))) {
      throw new Error(label + " must be a finite valid number");
    }
    return x;
  };
  if (!object(plan)) throw new Error("Plan must be an object");
  const legacy = !("schema_version" in plan);
  if (!legacy && plan.schema_version !== 1) throw new Error("Unsupported edit-plan schema_version");
  const fps = number(plan.fps, "fps", true);
  const total = number(plan.duration_frames, "duration_frames", true, true);
  if (!Array.isArray(plan.segments) || !plan.segments.length) throw new Error("Plan must contain nonempty segments");
  let cursor = 0;
  const ids = new Set();
  plan.segments.forEach((segment, index) => {
    if (!object(segment)) throw new Error("Segment must be an object");
    if (typeof segment.path !== "string" || !segment.path.trim()) throw new Error("Segment path required");
    if (!("id" in segment)) segment.id = "clip-" + String(index + 1).padStart(5, "0");
    if (typeof segment.id !== "string" || !segment.id || ids.has(segment.id)) throw new Error("Segment id must be unique");
    ids.add(segment.id);
    if (legacy && !("timeline_start" in segment)) segment.timeline_start = cursor;
    number(segment.timeline_start, "timeline_start", false, true);
    if (segment.timeline_start !== cursor) throw new Error("Timeline must be contiguous (no gaps or overlaps)");
    const length = number(segment.duration_frames, "segment duration_frames", true, true);
    const hasFrame = segment.source_in_frame !== undefined && segment.source_in_frame !== null;
    if (hasFrame) number(segment.source_in_frame, "source_in_frame", false, true);
    if (segment.source_in_seconds === undefined || segment.source_in_seconds === null) {
      if (!hasFrame) throw new Error("Source offset required");
      segment.source_in_seconds = segment.source_in_frame / fps;
    }
    const seconds = number(segment.source_in_seconds, "source_in_seconds");
    if (hasFrame && Math.abs(segment.source_in_frame - seconds * fps) > 0.500001) throw new Error("Conflicting source offsets");
    if ("source_fps" in segment) number(segment.source_fps, "source_fps", true);
    if (!("speed" in segment)) segment.speed = 1;
    number(segment.speed, "speed", true);
    if (!("speed_effect" in segment)) segment.speed_effect = {kind: "normal", speed: 1.0};
    const effect = segment.speed_effect;
    if (!object(effect) || !["normal", "slow_motion", "ramp"].includes(effect.kind)) throw new Error("Invalid speed_effect");
    const effectSpeed = number("speed" in effect ? effect.speed : 1, "speed_effect.speed", true);
    if (effect.kind === "normal" && effectSpeed !== 1) throw new Error("Normal effect must have speed 1");
    if ("source_end_seconds" in segment) {
      const end = number(segment.source_end_seconds, "source_end_seconds");
      if (end <= seconds || (effect.kind === "normal" && seconds + length / fps * segment.speed > end + 1e-7)) throw new Error("Invalid source range");
    }
    cursor += length;
  });
  if (cursor !== total) throw new Error("duration_frames does not match segment total");
  if ("duration_seconds" in plan && Math.abs(number(plan.duration_seconds, "duration_seconds", true) * fps - total) > 0.000001) throw new Error("Conflicting duration_seconds");
  plan.schema_version = 1;
  plan.duration_seconds = total / fps;
  return plan;
}
function preflightPlan(value) {
  const plan = validatePlan(value);
  const unsupported = plan.segments.filter(s => s.speed !== 1 || s.speed_effect.kind !== "normal").map(s => s.id);
  return {schema_version: 1, clips: plan.segments.length, fps: plan.fps,
    duration_frames: plan.duration_frames, duration_seconds: plan.duration_seconds,
    standalone_supported: unsupported.length === 0, unsupported_speed_clips: unsupported};
}
if (typeof module !== "undefined") module.exports = {validatePlan, preflightPlan};
