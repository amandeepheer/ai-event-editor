# Multiple editing styles

Six versioned presets are available in `ai_event_editor.styles.PRESETS`:
energetic event, cinematic, wedding, concert, social reel and documentary.

Custom styles are JSON files stored locally and loaded using `load_style`.
`blend_styles` combines two styles without training or downloading a model.

## Learn a style from finished videos

`learn_style([path1, path2], slug="my-style", name="My Style")`
estimates median shot length using FFmpeg scene-change detection. Save it with
`save_style(style, "my-styles")`.

This **only learns approximate cutting pace**. Other profile fields are inherited
from a preset. Flashing stage lights, pans and motion can create false positives.
Beat timing, transitions, speed ramps, colour grading and narrative sequencing
are not learned by this first implementation.

Profiles are currently data objects; the timeline planner is not yet wired to
use all their settings. A style picker and review interface are future work.

Only analyse videos you are entitled to use as references. Do not upload
private footage or copyrighted source material to the public repository.
