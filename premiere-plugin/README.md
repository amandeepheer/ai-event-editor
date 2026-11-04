# AI Event Editor — Premiere panel

The panel now runs setup, music selection, thumbnail review, Keep/Reject/Must include, supported typed instructions and local plan generation through the shared Python engine. It can then request a new editable native Premiere sequence. Editing can stay inside Premiere; opening the standalone desktop app or transferring JSON is not required.

On Windows, run `scripts/Configure-Premiere-Autostart.cmd` once. In the panel choose **Set up automatic start** and select the generated `engine-connection.json`. After Adobe launch consent, the panel remembers the configuration and automatically starts/reconnects to the helper when opened. Connection remains loopback-only. Manual startup/code pairing remain a fallback. Actual Windows launch and Adobe permission behavior still need host verification.

Load this directory with Adobe UXP Developer Tool. Native assembly and Source Monitor seek require Premiere 26.3+. Installed-host compatibility, UI rendering and Windows end-to-end operation remain unverified. Tests cover real local HTTP/FFmpeg behavior and explicit DOM/Adobe API test doubles.

Typed instructions support duration, pacing, style and category selection. Unknown instructions and unsupported slow motion, effects, titles or speech requests block generation with feedback. This is an offline rules interpreter, not a general language model or arbitrary timeline-editing assistant.

Existing saved-plan open/save and JSON validation remain available. Existing sequences/source marks are not edited, and nothing is automatically deleted or saved. New items or partial sequences can remain after a failed apply.

See [setup, capabilities and limitations](../docs/PREMIERE_WORKFLOW.md).
