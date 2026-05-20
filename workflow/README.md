# Chronicle Workflow

This workflow keeps the creative work in ChatGPT and uses the local importer only for mechanical validation and insertion into [`chronicle_data.json`](C:/Users/nchun/Desktop/Clover%20Stonefield/chronicle_data.json).

## Quick Open Viewer
If you want a double-clickable viewer launcher, use these files in the project root:
- [Open Clover Chronicle.cmd](C:/Users/nchun/Desktop/Clover%20Stonefield/Open%20Clover%20Chronicle.cmd)
- [Stop Clover Chronicle Server.cmd](C:/Users/nchun/Desktop/Clover%20Stonefield/Stop%20Clover%20Chronicle%20Server.cmd)

Double-clicking `Open Clover Chronicle.cmd` will:
- start a local `python -m http.server` in the project folder if one is not already running,
- open your default browser to the saga page through `http://127.0.0.1:8000/`,
- reuse the existing local server if the page is already available.

Double-clicking `Stop Clover Chronicle Server.cmd` will stop the tracked local server.

## Working Flow
1. Submit the adventure text to ChatGPT and ask for commentary.
2. Do as much commentary back-and-forth as you want.
3. If you want images, request them from ChatGPT and save the finished image files into [`images`](C:/Users/nchun/Desktop/Clover%20Stonefield/images).
4. By hand, compile the source material into a raw file named `era_[era #]_seg_[segment #]_raw.txt`.
5. Submit that raw file to ChatGPT and ask it to produce a new `.txt` file that matches [`template.txt`](C:/Users/nchun/Desktop/Clover%20Stonefield/template.txt) exactly.
6. Save ChatGPT's output as `era_[era #]_seg_[segment #].txt`.
7. Validate the finished `.txt` file with the importer.
8. If validation succeeds, preview the JSON with `--dry-run`.
9. If the preview looks correct, run the real import.
10. If the importer rejects a tricky file and you do not want to hand-fix it, hand that finished `.txt` file to Codex and let Codex inspect/import it with judgment.

## Recommended File Naming
- Raw source file: `era_2_seg_005_raw.txt`
- Template-matching final file: `era_2_seg_005.txt`

You can keep those files anywhere, but a simple convention is:
- raw files in [`workflow/raw`](C:/Users/nchun/Desktop/Clover%20Stonefield/workflow/raw)
- finished import-ready files in [`workflow/final`](C:/Users/nchun/Desktop/Clover%20Stonefield/workflow/final)

## What Goes In The Raw File
The raw file is for you and ChatGPT. It does not need to follow a strict parser format. It just needs to include the material ChatGPT will use to fill the real template:
- the adventure text
- the commentary exchange you want preserved
- any image titles
- any image alt text
- any image captions
- the image file locations you decided on

## What ChatGPT Must Return
The final `.txt` file should match [`template.txt`](C:/Users/nchun/Desktop/Clover%20Stonefield/template.txt) exactly in structure:

```text
[era number]
[/era number]

[segment number]
[/segment number]

[segment title]
[/segment title]

[location]
[/location]

[tagline]
[/tagline]

[adventure text]
[/adventure text]

[images]
[image title][/image title]
[image location][/image location]
[image alt text][/image alt text]
[image caption][/image caption]
[/images]

[commentary]
[assistant][/assistant]
[user][/user]
[/commentary]

[summary]
[/summary]

[state]
Location:
Weapons:
Gear:
Objective:
[/state]
```

## Suggested ChatGPT Prompt For The Raw File
Use something like this when you upload `era_[era #]_seg_[segment #]_raw.txt` to ChatGPT:

```text
Using the uploaded raw segment file, produce the final import-ready text file for my local Clover Chronicle workflow.

Rules:
- Match the structure of template.txt exactly.
- Output only the completed template text, with no explanation before or after it.
- Preserve the content decisions from the raw file.
- Keep the era number and segment number as plain numbers.
- In [images], repeat the four image fields once per image, in the same order shown in the template.
- In [commentary], include the assistant/user back-and-forth I want preserved, using repeated [assistant] and [user] blocks as needed.
- In [state], fill at least Location, Weapons, Gear, and Objective.
```

## Import Commands
Validate the finished file:

```powershell
python .\tools\chronicle_import.py validate .\workflow\final\era_2_seg_005.txt
```

Preview the exact JSON object that would be appended:

```powershell
python .\tools\chronicle_import.py import .\workflow\final\era_2_seg_005.txt --dry-run
```

Run the real import:

```powershell
python .\tools\chronicle_import.py import .\workflow\final\era_2_seg_005.txt
```

## Importer Rules For Template Files
- `era number` must be a positive integer.
- `segment number` must be a positive integer. The importer converts it to a zero-padded JSON number like `005`.
- The importer mechanically generates the segment slug as `segment-###`.
- The importer resolves the era number against the existing eras already present in [`chronicle_data.json`](C:/Users/nchun/Desktop/Clover%20Stonefield/chronicle_data.json).
- `adventure text` must contain at least one paragraph. Blank lines split paragraphs.
- `commentary` must contain at least one `[assistant]` or `[user]` block.
- `images` may be empty. If present, they must appear as repeated groups of:
  - `[image title]`
  - `[image location]`
  - `[image alt text]`
  - `[image caption]`
- `state` must contain at least:
  - `Location`
  - `Weapons`
  - `Gear`
  - `Objective`
- Image locations are checked relative to the project root unless they are absolute paths.
- Duplicate segment numbers and duplicate segment slugs are rejected.
- The importer creates a timestamped backup in [`workflow/backups`](C:/Users/nchun/Desktop/Clover%20Stonefield/workflow/backups) before writing.

## Notes
- The importer still understands the older all-uppercase packet format for backward compatibility, but the template-based `.txt` workflow is now the preferred path.
- The importer does not invent story content. It only validates, converts, backs up, and appends.
