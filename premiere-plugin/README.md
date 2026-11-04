# AI Event Editor — Premiere panel

Version 0.5.1 changes the network permission from the port-qualified entry to `http://127.0.0.1`. The request client independently enforces `http://127.0.0.1:8765` on every call and rejects alternate hosts/ports and redirects. A manifest permission denial now stops automatic launching and displays an update-panel message. Reinstall the updated CCX and cold-restart Premiere; Adobe permission matching requires the user's installed-host retest.

The panel now runs setup, music selection, thumbnail review, Keep/Reject/Must include, supported typed instructions and local plan generation through the shared Python engine. It can then request a new editable native Premiere sequence. Editing can stay inside Premiere; opening the standalone desktop app or transferring JSON is not required.

Version 0.5 adds **Use selected project media**: select imported footage/audio or bins in the Project panel. Nested bins are traversed read-only; the local helper separates videos and audio-only music candidates. Choose music when ambiguous, type instructions and build. Build prepares footage automatically if needed; no existing timeline is required. Whole linked sources are used; source marks/subclip bounds/effects/proxy/interpretation overrides are not copied. The adapter imports fresh source references into its own bin and preserves existing items. See [Project panel workflow](../USER_GUIDE.md#use-imported-project-panel-media-version-05).

On Windows, run `scripts/Configure-Premiere-Autostart.cmd` once. In the panel choose **Set up automatic start** and select the generated `engine-connection.json`. After Adobe launch consent, the panel remembers the configuration and automatically starts/reconnects to the helper when opened. Connection remains loopback-only. Manual startup/code pairing remain a fallback. Actual Windows launch and Adobe permission behavior still need host verification.

Load this directory with Adobe UXP Developer Tool. Native assembly and Source Monitor seek require Premiere 26.3+. Installed-host compatibility, UI rendering and Windows end-to-end operation remain unverified. Tests cover real local HTTP/FFmpeg behavior and explicit DOM/Adobe API test doubles.

Typed instructions support duration, pacing, style and category selection. Unknown instructions and unsupported slow motion, effects, titles or speech requests block generation with feedback. This is an offline rules interpreter, not a general language model or arbitrary timeline-editing assistant.

Existing saved-plan open/save and JSON validation remain available. Existing sequences/source marks are not edited, and nothing is automatically deleted or saved. New items or partial sequences can remain after a failed apply.

See [setup, capabilities and limitations](../docs/PREMIERE_WORKFLOW.md).

See [native-control audit](../docs/PREMIERE_NATIVE_AUDIT.md) for effect/transition, framing, tracking, retiming, title, audio and export routes and manual steps. **Check native tools** reads API presence and installed catalogs without a helper connection or project mutations; **Save tool report** saves the inventory locally. It does not certify editing behavior. Existing native adapters remain experimental.

The AI Edition adds optional managed CLIP package/model setup and local Ollama/Qwen interpretation. Enable the language checkbox only after installing Ollama/Qwen. Unknown phrasing uses a validated schema; unsupported editing features remain blocked. See `../docs/AI_ADDON.md`.
