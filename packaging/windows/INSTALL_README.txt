AI EVENT EDITOR - AI EDITION / ADD-ON PREVIEW 0.4.0

This installer includes the updated basic program plus a managed Python runtime
for optional AI packages. It can replace the earlier basic installer; no separate
system Python or terminal commands are required. Save your work and close an
older running engine before upgrading. It does not uninstall your footage/data.

1. Open "AI Event Editor Setup and Status" from the Start menu.
2. Click "Finish basic setup". This configures automatic startup and downloads
   approximately 81 MB of media tools if needed.
3. Click "Install Premiere panel" and approve Adobe Creative Cloud's CCX prompts.
4. In Premiere 26.3+, open Window > UXP Plugins > AI Event Editor. Enable plugin
   Developer Mode if Adobe requires it for this preview. Select "Set up automatic
   start", then engine-connection.json from %LOCALAPPDATA%\AIEventEditor.

OPTIONAL AI FOOTAGE SUGGESTIONS

5. In Setup and Status choose CPU or NVIDIA mode and click "Install / repair
   CLIP AI". CPU downloads hundreds of MB of packages plus the model; NVIDIA
   CUDA packages can be several GB. NVIDIA mode needs a compatible driver.
   The model is downloaded once, then real inference is tested before readiness.
6. After success, reconnect/reopen the Premiere panel. Enable cached local AI
   and prepare footage. Categories are suggestions and still require review.
   The worker releases its model/GPU memory when the analysis operation ends.
   If GPU setup fails, check your driver or choose the smaller/slower CPU option.

OPTIONAL LOCAL LANGUAGE UNDERSTANDING

7. Click "Install Ollama" (about 1.7 GB). Complete the vendor's installer window.
   If Ollama is already installed, skip this button.
8. Click "Download Qwen3 8B language model" (about 5.2 GB). This uses Ollama's
   local service. Downloads are optional and require internet and free disk space.
9. Enable "Use local Ollama/Qwen" in the Premiere panel for broader phrasing.
   Existing simple instructions still use deterministic rules. Local model output
   is restricted to supported settings and must be reviewed. No cloud-model or
   paid API fallback is used. Requests for unfinished effects remain blocked.

Basic workflow: add footage/music, choose length/style/pacing, prepare and review
moments, type optional instructions, build, then confirm a NEW Premiere sequence.
Finish and export normally in Premiere. Save your Premiere project normally.

Not implemented: actual slow motion/speed ramps, visual effects, native titles,
interview/speech edits, arbitrary AI changes to an existing Premiere timeline.
Downloading a model does not create those missing editing functions.

The program, installers and downloads are development previews. Automated CPU
inference can be verified in CI; RTX 5070 operation, real Qwen performance and
native installed Premiere behavior still need checks on the user's computer.
The installer is unsigned; normal Windows/Adobe permission prompts may appear.

Uninstall removes installed program files, not original footage/Premiere projects
or per-user pairing, media-tool and model-cache data under AppData. Models and
packages occupy disk space and are not automatically removed by upgrades.
Keep engine-connection.json private; it contains the local pairing credential.

Downloaded software/models:
FFmpeg: https://github.com/BtbN/FFmpeg-Builds
Torch: https://pytorch.org/get-started/previous-versions/
CLIP: https://huggingface.co/openai/clip-vit-base-patch32
Ollama: https://github.com/ollama/ollama
Qwen: https://ollama.com/library/qwen3:8b
Their respective notices and licences apply; downloads run directly on your PC.

Project guide:
https://github.com/amandeepheer/ai-event-editor/blob/main/USER_GUIDE.md
