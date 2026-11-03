# Local automatic analysis (prototype)

Install Python 3.12 and FFmpeg, then from the repository:

```powershell
pip install -e ".[vision,media,test]"
ai-event-editor analyze "C:\\Event\\Footage" --output shot-candidates.json
```

The worker loads CLIP once, samples approximately every four seconds, and saves suggested shot labels to JSON. Initial model weights download to the computer once. Video stays local. This is a **candidate generator**, not an end-to-end automatic editor: the output needs human review, and candidates may overlap or be too short for the planner.

After curating a `shots.json` array containing sufficient non-overlapping labelled footage:

```powershell
ai-event-editor build shots.json --duration 120 --beats beats.json --music "C:\\Event\\music.wav" --xml recap.xml
```

Duration accepts any whole number of seconds from 30 through 300. The planner does not reuse identical source windows. Longer videos require more source footage in every required category. Beat matching currently affects only section boundaries. The XML exporter assumes 25fps and is **not verified in Premiere**.

Review AI categories, respect music licensing, and verify timeline output before client delivery.
