# AI Event Editor — Premiere panel

Experimental Adobe UXP integration. Load this directory with Adobe UXP Developer Tool.

Prepare footage, music, length/style/pacing and shot decisions in the local desktop workflow (`python -m ai_event_editor.desktop`). Click **Save edit for Premiere**, then **Open reviewed edit** in the panel. No manual JSON authoring or copy/paste is needed; existing JSON validation remains available.

After reviewing the plan, tick the confirmation and choose **Create new sequence**. This uses native subclips and timeline actions, not a flattened MP4 or XML import. Video subclips exclude source audio; the optional music subclip uses the selected excerpt. Existing sequences and source marks remain unchanged. New media items and partial sequences can remain after a failure; nothing is automatically deleted or saved.

Native assembly requires Premiere 26.3+ (subclip API). The manifest retains the older minimum for inspect/validate functionality. Native behavior has **not** been verified in installed Premiere. Tests use documented API signatures and a mock host; they do not prove runtime compatibility. Default Premiere preset geometry is used; inspect framing, music, trim points and timeline duration before delivery.

Speed effects and native titles are explicitly rejected rather than silently discarded. Effects intensity, interviews and direct engine communication are later work. The duration and instruction scaffold does not modify imported plans; set supported controls in the desktop workflow.

See [workflow details](../docs/GUIDED_WORKFLOW.md).
