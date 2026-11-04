# AI Edition / add-on installer

Version 0.4 adds command-free setup of optional local CLIP and local Ollama/Qwen interpretation. The installer is an updated full basic program plus a managed AI runtime, so users do not need to juggle a separate base installation. Existing basic, source and standalone workflows remain supported.

## User flow

Run the AI Setup executable, finish basic setup and update/install the Adobe panel. In **Setup and Status**, choose CPU or NVIDIA and **Install / repair CLIP AI**. Packages and CLIP weights download to this computer and real inference verifies the selected device before the engine reports AI available. Reconnect the Premiere panel and enable cached local AI suggestions.

The installed AIAddon folder contains an isolated copy of the build's Windows CPython runtime, standard library, a pip bootstrap wheel and the project's worker code. It does not use a system Python. ML packages install only in that managed runtime. A separate worker loads CLIP for each analysis batch, uses cached weights offline during analysis, and exits afterward to release resources. Classification is bounded to eight frames per model batch to limit GPU-memory use. It is not trained to reliably know which guest/moment matters to an event.

CPU packages require hundreds of MB plus model weights; NVIDIA CUDA packages can require several GB and a compatible driver. NVIDIA uses the official Torch 2.10 CUDA 13.0 wheel index; CPU uses the CPU index. A failed setup leaves AI unavailable rather than silently claiming readiness. The basic unranked workflow remains usable. Setup progress/logs report failures; choose CPU explicitly if GPU support is unavailable.

Ollama is optional and separate. **Install Ollama** downloads a pinned/checksummed vendor installer (about 1.7 GB) and opens its normal installation window. If already installed, skip it. **Download Qwen3 8B language model** uses the local Ollama API to pull about 5.2 GB of weights. These are real disk/network downloads, not an AI subscription. They are not downloaded merely by installing the AI Edition or by opening the panel.

## Typed language interpretation

The panel's local-language checkbox opts into Ollama for broader phrasing. Clear requests already understood by rules remain deterministic, avoiding unnecessary model loads. Unknown phrasing can be translated into a constrained JSON schema: duration, one style, one pacing, category inclusion/exclusion and unsupported requests. Every returned field is validated. Known unsupported requests and invalid direct settings cannot be waived by the model. The model cannot issue shell/file commands or invent engine actions. Proposed settings and categories still require human review; model interpretation may be wrong.

Ollama calls use only `127.0.0.1:11434`, disable proxy forwarding/redirects and specify the local `qwen3:8b` tag. There is no cloud API or cloud-model fallback. Model responses are size-limited and schema-validated. `keep_alive: 0` requests unloading after interpretation. Long interpretation/build operations use polled helper jobs instead of blocking a short panel HTTP call. No original media is sent to the language model; only instruction text is used.

Unavailable Ollama, missing weights, malformed output and unsupported requests produce errors. Disable local-language mode to continue with explicit controls/rules. Slow motion, speed ramps, effects, grading, titles, speeches and arbitrary timeline editing are still unfinished; model downloads do not implement them.

## Storage and updates

The managed runtime/packages are in the installed app's AIAddon folder. CLIP cache/readiness data live under `%LOCALAPPDATA%/AIEventEditor`; Ollama manages its own model storage. A setup marker prevents half-installed packages from being advertised as ready. Reconnect the panel after setup. Save work and stop an older engine before updating executable files or AI packages; do not analyze an event while repairing packages.

Uninstall does not remove original footage or Premiere projects. Per-user caches/configuration are retained for deliberate management. Updating the application retains site-packages through installer file copying; repair/reverify if runtime readiness is lost. This preview does not yet implement transactional package rollback or automatic review-session recovery.

## Verification limits

Unit tests cover validation, offline routing, async interpretation jobs, package/readiness rules, setup failure and worker contracts. The Windows installer job installs the real CPU Torch/Transformers/Pillow packages and CLIP model in the shipped managed runtime, verifies inference and prepares real synthetic footage through the installed authenticated engine. It publishes only after the smoke test succeeds. NVIDIA GPU/driver behavior and the real Ollama installer/Qwen performance remain user-machine verification; those multi-GB downloads are not repeated in CI. Native Adobe/real-camera operation remains unverified.

## Primary references

- https://pytorch.org/get-started/previous-versions/
- https://huggingface.co/openai/clip-vit-base-patch32
- https://docs.ollama.com/capabilities/structured-outputs
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/windows
