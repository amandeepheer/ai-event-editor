# Premiere-first local workflow

The Premiere panel now contains footage/music setup, thumbnail review, typed instruction feedback, local edit generation and native new-sequence creation. There is no requirement to open the standalone desktop editor or manually transfer JSON. Finish, adjust and export using Premiere's normal editing tools after the sequence is created.

This is an integrated development preview, not a verified installer release. Automated tests cover the Python engine, the real loopback HTTP service, panel events using explicit DOM/UXP test doubles, and native sequence assembly using an Adobe API test double. They do not establish installed Premiere compatibility or Windows visual quality.

## First-time setup on Windows

1. Install Python 3.10+ and FFmpeg (including FFprobe) on PATH. From the repository directory run `python -m pip install -e .`.
2. Start the processing helper with `python -m ai_event_editor.service`, or double-click `scripts/Start-Local-Engine.cmd`. Keep it running; the window can be minimized. It prints a pairing code. This helper is not the standalone editor.
3. Load `premiere-plugin/` through Adobe UXP Developer Tool and open a Premiere project. Paste the pairing code into the panel and click **Connect**. The service uses port 8765; if the port is already occupied, close the duplicate helper rather than launching many copies.
4. **Add footage**, **Choose music**, set music start/end, output length (30–300 seconds), style and pacing. **Preview in Premiere** opens source media in Premiere's Source Monitor at the selected time. Playback stays under Premiere's controls; the displayed end time is a review guide, not a playback lock.
5. Click **Prepare moments**. The default creates unranked windows and local thumbnails. Optional cached CLIP suggestions require vision extras and already downloaded model weights; the panel does not download a model.
6. Review thumbnails, preview moments, correct categories and choose Keep, Reject or Must include. Reviews are paginated to keep the panel usable with larger events. Keep is eligible; Must include guarantees an excerpt from the moment when it fits.
7. Type an optional instruction and click **Review instructions** to inspect supported changes. **Build reviewed edit** sends the current choices to the local engine, applies supported instructions and displays the plan summary. It does not change Premiere's timeline.
8. Confirm **Create a new sequence**, then click **Create Premiere sequence**. Individual clips and the selected music excerpt are assembled in a new sequence. Continue editing and export in Premiere. Default Premiere preset geometry is used, so inspect framing.

Native creation and Source Monitor seeking require Premiere 26.3+ and still need testing in an installed Premiere environment. Earlier compatible UXP hosts can retain inspect/validate functions. Source files, existing sequences and source marks are not overwritten. Failure can leave newly imported items or a partial new sequence for review; nothing is automatically deleted or saved.

The helper currently requires manual startup and pairing. A packaged installer, automatic companion startup, secure saved pairing and automatic session recovery are not implemented. Review state lives in the open panel and bounded helper sessions. Save the final edit with **Save edit** before closing; **Open saved edit** and legacy JSON validation remain available. Standalone review sessions and the standalone editor remain available separately.

## Supported typed instructions

The current interpreter is a deterministic offline parser, not a general language model. Supported examples:

- `Make a one-minute cinematic recap with energetic pacing.`
- `Create a 30-second wedding highlight with calm pacing.`
- `Make a 2-minute concert recap with balanced pacing.`
- `Include crowd. Exclude stalls.`

Supported controls are duration, one style, one pacing choice and explicit include/exclude category commands. `Include crowd` pins one kept crowd moment, not every crowd shot. User-rejected moments are not automatically restored. Repeated category commands can be used for multiple categories. Category names are drone, stalls, performance, dancing, crowd and finale. Missing categories never block the planner by themselves.

Unknown phrases, conflicting settings, missing requested categories and unsupported features are reported and block generation. Slow motion, speed ramps, titles/captions, visual effects, grading and interview/speech editing are not implemented through typed instructions. Style names affect pacing/coverage, not native colour grades or transitions. `Make a cinematic recap with slow motion` will report that slow motion is unavailable instead of silently ignoring it.

Instructions regenerate a proposed edit from reviewed source moments. They do not edit arbitrary existing Premiere timeline elements, interpret every natural-language command, preserve manual edits through AI regeneration or provide a chat assistant. Existing sequences remain available because each apply action creates a new sequence.

## Local service contract

The stdlib helper binds only `127.0.0.1`. The panel declares only `http://127.0.0.1:8765` in its network permissions. Files are read on the local computer and paths/thumbnail data travel only over loopback. No external API, paid service, model download or media upload is used by this connection.

Every endpoint requires the pairing token in an Authorization header. Tokens are never sent in URLs or request logs. The helper also validates the Host header and restricts browser origins, provides no arbitrary file-serving endpoint and rejects unknown/duplicate shot IDs or attempts to replace source paths/ranges through review patches. Thumbnail PNGs are returned as data URLs in authenticated job results. The local pairing token is stored in the current user's application data and displayed by the helper; keep it private. Panel pairing is held only in memory.

Long operations run in one background worker with status polling; concurrent operations are rejected. Completed job metadata is bounded to 16 jobs and four review sessions. Expired sessions produce a message to prepare footage again. Temporary thumbnails are removed when the helper shuts down. A disconnected panel does not automatically resubmit processing or mutate a timeline.

Endpoints (all under `/v1`): health, prepare, interpret, build and jobs/{id}. Prepare/build return job IDs; interpret returns proposed supported changes and unsupported requests. Source ranges remain authoritative in the helper and only decision/category patches are accepted.

## Remaining verification

Test on the user's Windows/Premiere computer: UXP network origin/permission behavior, pairing, file picker access, thumbnail display, Source Monitor preview, mixed-fps Sony/drone sources, native subclips, frame rate/framing, music offsets, partial failures, preservation of an existing client sequence and normal Premiere export. macOS HTTP restrictions are outside this Windows preview's verified scope.

Adobe references checked for this implementation:
- https://developer.adobe.com/premiere-pro/uxp/resources/recipes/network/
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/sourcemonitor
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/project
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/clipprojectitem
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/sequenceeditor
