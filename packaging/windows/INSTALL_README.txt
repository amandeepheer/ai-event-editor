AI EVENT EDITOR - WINDOWS DEVELOPMENT PREVIEW

1. Open "AI Event Editor Setup and Status" from the Start menu.
2. Click "Finish setup". The Python engine is included. On first setup it
   downloads approximately 81 MB of FFmpeg/FFprobe media tools directly from
   the upstream publisher, verifies their checksum and configures startup.
   Internet is required for this initial download. There is no subscription.
3. Click "Install Premiere panel". Adobe Creative Cloud Desktop opens the
   included .ccx package. Accept Adobe's installation/permission prompts.
4. Open Premiere 26.3 or newer, then Window > UXP Plugins > AI Event Editor.
   Enable Premiere's plugin Developer Mode if Adobe requires it for this preview.
5. Click "Set up automatic start" and select engine-connection.json in:
   %LOCALAPPDATA%\AIEventEditor
   Use the setup window's "Open connection-file folder" button to locate it.
   Keep this private file: it contains your local pairing credential.
6. Next time the panel opens it reconnects or launches the engine automatically.

Editing: Add footage, choose optional music and length/style/pacing, prepare
moments, review Keep/Reject/Must include, type supported instructions, build
and confirm creation of a new sequence. Finish and export normally in Premiere.
Example instruction: Make a one-minute cinematic recap with energetic pacing.

Included: basic local planning engine, setup/status app and Premiere .ccx package.
Not included: Premiere/Creative Cloud, CLIP GPU packages/weights, Ollama or a
standalone MP4-rendering application. Advanced natural-language AI, slow motion,
effects, titles and speech editing remain unfinished. Default analysis creates
unranked moments; it does not identify the best emotional moment automatically.

This is an unsigned development-preview installer. Windows and Adobe may display
publisher/permission prompts. Installed Premiere compatibility and real footage
still need verification. A successful installer smoke test is not proof of a
working native Premiere workflow. Existing client sequences are not overwritten;
review new timelines before delivery.

Moving/uninstalling the app can invalidate automatic startup. Uninstall removes
installed program files, not original footage, Premiere projects or per-user
pairing/media-tool data under %LOCALAPPDATA%\AIEventEditor. Review/save your work
and close a running engine before updating. This installer does not silently
terminate a processing engine or delete event data.

Downloaded media tools: BtbN FFmpeg LGPL shared Windows build (8.1 branch).
https://github.com/BtbN/FFmpeg-Builds
The downloaded archive retains its publisher's licence/notices. Binaries are
retrieved directly during setup, not embedded in this installer.

Project/user guide:
https://github.com/amandeepheer/ai-event-editor/blob/main/USER_GUIDE.md
