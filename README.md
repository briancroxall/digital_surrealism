# digital_surrealism

Tools for students in *Introduction to Digital Humanities* to make "digital
surrealism" images of a film, following Kevin L. Ferguson, ["Digital
Surrealism: Visualizing Walt Disney Animation Studios"](https://dhq.digitalhumanities.org/vol/11/1/000276/000276.html)
(*DHQ* 11.1, 2017) and ["To Cite or to Steal? When a Scholarly Project Turns Up in a Gallery"](https://hyperallergic.com/to-cite-or-to-steal-when-a-scholarly-project-turns-up-in-a-gallery/) (Hyperallergic, 30 June 2016). 

Rather than using Ferguson's exact process, however, this small application uses `FFMPEG` to extract one frame from every two seconds of video (Ferguson uses Quicktime) and then uses JavaScript to create a summed image (Ferguson uses ImageJ). The summing process also produces bar codes of the film, which is an innovation that I believe I picked up from my colleague, Jeremy Browne. 

This application was developed using Claude Code. Since I have been using an assignment based on Ferguson's work for nine years, I'm well acquainted with the pain points for my students, and this instantiation will hopefully eliminate as many of those as possible.

Students start with an MKV ripped by MakeMKV and end with:

- a folder of frames (one every 2 seconds)
- a summed image of all the frames
- three barcodes (center-column slice, center-row slice, average color)

## Status

| Part | What it does | Status |
|---|---|---|
| Frame extractor (local, lab Macs) | MKV → cropped, square-pixel frames | Done: command line, web interface, and lab launcher |
| Image maker (browser, GitHub Pages) | frames → summed image + barcodes | Done; published 2026-11-09 |

## Frame extractor

Requires [ffmpeg](https://ffmpeg.org) and [uv](https://docs.astral.sh/uv/).
Runs on macOS.

### In the browser (for students)

On a lab Mac, double-click **Digital Surrealism** on the Desktop. That's
`lab/Digital Surrealism.command`, which runs the command below for you.
Setting up a Mac for this is in [lab/INSTALL.md](lab/INSTALL.md).

Or, from the repo folder in Terminal:

```
uv run digital-surrealism app
```

This opens the extractor in your web browser. It runs only on your Mac
(at `http://127.0.0.1:5150`), and nothing goes over the internet. Leave the
Terminal window open while you work, and press Control-C in it to quit.

The page has five steps:

1. **Choose film.** A Finder window opens to pick the MKV.
2. **Check crop.** The tool finds the black bars and shows six moments from
   the film, each as the full frame with a red box (what will be kept) beside
   the cropped result. The second image shows the crop even when a red box
   would vanish against red scenery. If the crop is wrong, buttons move each
   edge in or out by 2 pixels (counted in the film's stored size) and redraw
   the previews.
3. **Choose size.** DVD size, or for a Blu-ray, optionally full resolution.
   The page says how many frames you'll get, their size, and roughly how much
   disk space they'll take.
4. **Choose where to save.** Pick a place, such as your Desktop. The tool
   makes a folder named after the film there (for example,
   `f4_first-steps_frames`). It refuses a folder that already has frames and
   warns if the disk looks too full.
5. **Extract.** A progress bar with the time left. **Cancel** asks for
   confirmation, then stops and deletes the partial frames, because an
   incomplete folder would look finished and give a summed image of only part
   of the film. If extraction fails (for example, the disk fills up), the
   partial frames are deleted too. Only the tool's own `frame_*.png` files are
   deleted; anything else in the folder is left alone.

The step names at the top of the page are clickable while you're choosing
the crop, size, and save location, so you can go back (or forward again to
any step you've already reached). Going back to step 1 shows the current film;
nothing is lost unless you actually pick a different one.

You can close the page during extraction and reopen it to check on progress.

### On the command line

Find the black bars and save preview images (red box = what will be kept,
plus each moment as it will look once cropped):

```
uv run digital-surrealism detect film.mkv --previews previews/
```

Extract frames:

```
uv run digital-surrealism extract film.mkv frames/
```

Unlike the browser version, `extract` writes frames straight into the folder
you name, and a stopped run (Control-C) leaves its partial frames in place.

Options for `extract`:

- `--crop W:H:X:Y` uses a crop you give instead of detecting one
- `--full-res` keeps Blu-ray frames at full resolution (see below)

### How it works, and the choices built into it

**Finding the black bars.** ffmpeg's `cropdetect` filter reports the
smallest rectangle containing everything brighter than near-black (24 on
a 0–255 scale, ffmpeg's default). One sample can be fooled by a dark scene, so
the tool:

1. samples 30 evenly spaced moments between 5% and 95% of the runtime
   (skipping opening and closing credits), looking at 15 frames each time;
2. throws away impossible answers, which come from all-black frames
   (negative sizes, or a picture less than a quarter of the frame);
3. keeps the answer that the most samples agree on. On a tie, it keeps the
   larger picture, so it crops off less.

It reports how many samples agreed and warns if fewer than half did.

**Extracting frames.** One ffmpeg pass does, in order:

1. **Deinterlace** frames flagged as interlaced (common on DVDs). Others pass
   through untouched.
2. **Keep one frame every 2 seconds** (`fps=0.5`, as in Ferguson's 1:60 ratio
   for 30 fps video). A 90-minute film gives about 2,700 frames.
3. **Crop** the black bars.
4. **Make pixels square.** DVDs store 720 pixels across but are shown wider
   (for widescreen) or narrower (for 4:3). Image files can't record that, so
   the frames are resized to the shape the film actually has on screen (see
   "Why DVD frames come out squeezed," below).
5. **Scale to DVD size** (default). The *full* frame is scaled so it would
   be 480 pixels tall, then cropped, so a widescreen film comes out shorter
   than 480. A 2.39:1 film is about 853 × 357. A Blu-ray is scaled down by
   the same rule, so every student's frames are comparable. Nothing is
   ever scaled up. With `--full-res`, a Blu-ray keeps its full size (for
   example, 1920 × 804), with folders about 4–5× larger.

Frames are saved as `frame_0001.png`, `frame_0002.png`, … The tool refuses to
write into a folder that already has frames, so two films can't get mixed.

### Why DVD frames come out squeezed

Every NTSC DVD stores the same frame, 720 × 480 pixels, whatever the shape of
the film. Each disc also carries a stretch instruction, the *sample aspect
ratio* (SAR), that tells whatever plays it how wide each pixel should be shown:

- **Widescreen (16:9) DVDs** are stretched *wider*: 720 → about 853 pixels.
  This is what "anamorphic widescreen" on a DVD case means.
- **4:3 DVDs** are narrowed slightly: 720 → about 640 pixels.

DVD players, VLC, QuickTime, HandBrake's preview, and TVs all follow the
instruction, so the film looks right when you watch it. PNG files have nowhere
to store it, though, so extracting frames with a plain ffmpeg command saves
them at the stored 720-pixel width. On a widescreen DVD, everything in them
(faces, circles) is about 16% too narrow.

The stretch only fixes the shape of the full frame (16:9). The black bars fill
the gap between that and the film's own shape (for example, 2.37:1), so
cropping is a separate step.

Blu-rays usually store square pixels (1920 × 1080), so their SAR is 1 and
nothing needs stretching.

**In the code** (`extract.py`): `output_size()` multiplies the cropped width by
the SAR that ffprobe reports. Then ffmpeg's `scale` filter resizes each frame
to that width, and `setsar=1` labels the result as square pixels. Done by
hand, the equivalent for the 2.37:1 widescreen DVD we tested is (the crop
numbers differ from film to film):

```
-vf "fps=0.5,crop=720:360:0:58,scale=853:360,setsar=1"
```

**Checked on a real DVD** (2026-11-05). We extracted frames from the same MKV
three ways:

| | Bars removed? | Correct width? |
|---|---|---|
| This tool | yes | yes (853 × 360) |
| ffmpeg directly on the MKV | no | no (720 × 480) |
| HandBrake → MP4, then ffmpeg | yes | no (720 × 360) |

All three captured the same moments of the film, and once their size and
cropping were matched, the pixels agreed closely. Frames made the older ways
(including summed images from past semesters) are squeezed horizontally.

## Image maker

A web page (`web/`) that turns a folder of frames into a summed image and
three barcodes. Everything happens in the browser on the student's own
computer; no frames are uploaded. It's published at
<https://briancroxall.github.io/digital_surrealism/> (see "Publishing the
Image maker" below), and the extractor's Done screen links to it.

To try changes before publishing them, run it locally:

```
uv run python -m http.server 8000 -d web -b 127.0.0.1
```

then open <http://127.0.0.1:8000>. (Opening `index.html` straight from Finder
doesn't work: browsers only run the page's background worker from a web
address.) Press Control-C to stop the server.

Choose the frames folder, then click **Make images**. The page uses every PNG
in the folder, sorted by number (`frame_2` before `frame_10`), so filename
order is film order. It stops with a message if the frames aren't all the same
size. It reads each frame once and makes all four images in that one pass.

**Saving.** Each image has its own Save button, and **Save all four…** saves
them together, named after the frames folder:

- `<folder>_summed.png`
- `<folder>_barcode_horizontal.png`
- `<folder>_barcode_vertical.png`
- `<folder>_barcode_average.png`

In Chrome and Edge, "Save all four" asks for a folder and writes the files
straight into it, asking first if any of those files are already there. Chrome
won't let a page write straight into Downloads, Documents, or Desktop (it says
they contain system files), so choose or make a folder inside one of them; the
page says so under the button. Safari,
Firefox, and Brave don't allow pages to write into folders (Brave turns it
off), so there the button downloads the four files to the Downloads folder.
Safari may ask once whether to allow several downloads. Saving again downloads
new copies (named `… (1).png`); the browser doesn't replace the earlier ones,
and the page can't see what's already in Downloads to warn you.

### The summed image

The page:

1. **Averages the frames.** For every pixel, it adds up the red, green, and
   blue values of all the frames and divides by the number of frames.
2. **Stretches each colour separately.** An average is dim and low in
   contrast. For the F4 DVD, for example, red in the average ran only from
   about 40 to 76 (on a 0–255 scale). Each colour's darkest value becomes 0 and
   its brightest becomes 255, with everything in between spaced evenly, then
   rounded to whole numbers. A red value of 58 (halfway from 40 to 76) becomes
   about 128.

Because each colour is stretched by its own amount, the result is also
colour-balanced, not just brightened: a film with a blue cast loses some of
it. That is an interpretive choice built into the method, inherited from the
recipe below. If a colour is perfectly flat (the same everywhere), it is left
as it is.

On the page, "How this image was made" lists each colour's range before
stretching.

**Relation to the ImageMagick recipe used in past semesters.** Earlier
classes made summed images with:

```
magick frames/*.png -channel R -evaluate-sequence Mean -auto-level split_avg_R.jpg
magick frames/*.png -channel G -average -auto-level split_avg_G.jpg
magick frames/*.png -channel B -average -auto-level split_avg_B.jpg
magick split_avg_* -evaluate-sequence Mean -auto-level split_avg_RGB.png
```

The first three commands each average the frames, keep only one colour
(ImageMagick sets the other two to zero), and stretch it from 0 to 255
(`-auto-level` is a straight-line stretch). The last command averages the
three one-colour images, which divides each colour by 3, and stretches again,
which multiplies it back, so it simply reassembles the three stretched
colours. The net effect is steps 1–2 above.

We checked this on 344 frames of the F4 DVD (2026-11-06). Running the recipe
with PNGs in place of the JPGs gave exactly the same image as steps 1–2 (no
pixel differed). The JPG files in the recipe only add compression error: on
average 2.9 out of 255, 99% of values within 10, at most 20. The Image maker
leaves that error out. (`-average` is an older name for
`-evaluate-sequence Mean`.)

### The barcodes

One stripe per frame, in film order. For the F4 DVD frames from our extractor
(3,442 frames of 853 × 360):

| Barcode | Each stripe is | Size |
|---|---|---|
| Horizontal | the frame's centre column, left (start) to right (end) | 3,442 × 360 |
| Vertical | the frame's centre row, top (start) to bottom (end) | 853 × 3,442 |
| Average colour | the frame's average colour, left to right | 3,442 × 360 |

Choices built in:

- **Not stretched.** Unlike the summed image, the barcodes show the frames'
  own colours. Slices come from single frames, so they already have full
  contrast. The average-colour barcode looks darker and duller than the summed
  image, but it shows each film's real colours over time, so barcodes of
  different films can be compared directly.
- **"Centre" when the size is even.** A frame 720 wide has two middle columns
  (360 and 361, counting from 1); the barcode uses the right-hand one, 361.
  An odd size has a true middle (column 427 of 853). Rows work the same way:
  row 181 of 360 (the lower of the two middle rows).
- **Average colour** is the plain average of the frame's red, green, and blue
  values, the same arithmetic as the summed image, rounded to whole numbers
  (halves round up).

### Why the Image maker ignores colour labels

A PNG file can carry a label saying which colour standard its numbers are in.
Frames made by ffmpeg from a HandBrake MP4 are labelled as NTSC video colour
(the standard for DVDs). Frames our extractor made from the F4 MKV have no
label, because the MKV doesn't record a colour standard, but other discs
(Blu-rays especially) often do.

Browsers treat the label differently. Chrome, Firefox, and Brave give the page
the numbers stored in the file, as asked. Safari converts the colours from the
labelled standard to the one it uses for display, which changes the numbers
slightly. On the 3,442 labelled F4 frames (2026-11-07), Safari's summed image
differed from Chrome's in 54% of its colour values, by up to 6 out of 255, and
every colour's range before stretching was 1.5–2.7 points lower.

For this method the frames are data, not pictures to display: ImageMagick's
recipe, Python, Chrome, and Firefox all use the stored numbers, and every
student should get the same image whatever browser they use. So the Image
maker removes the label from its in-memory copy of each frame before reading
it (the files themselves are not changed). The page reports how many frames
had a label under "How this image was made."

With labels removed, Chrome, Firefox, and Safari each matched the Python
reference exactly on the F4 frames: no pixel differed. (Brave, which is built
on Chrome, showed the same colour ranges as Chrome on the page but wasn't
put through the pixel-by-pixel check.)
We tested this by checking removal on its own first. Safari matched exactly
on 344 frames with their labels removed and differed by up to 7 on the same
frames with labels kept.

The labels removed are `cICP`, `cHRM`, `gAMA`, `iCCP`, `sRGB`, `mDCV`, and
`cLLI` (`web/png.js`).

## Development

```
uv run pytest
```

The tests build small synthetic films with ffmpeg (test patterns padded with
black bars, including a dark scene) and check crop detection, frame sizes, and
frame counts. The web interface tests (`tests/test_app.py`) run the whole
five-step flow, with the Finder windows replaced by fixed answers, and check
nudging, refused folders, and that cancelling deletes only the tool's own
frames. The Finder windows themselves have to be tried by hand.

The Image maker's arithmetic has a Python twin, `tools/reference.py`, tested in
`tests/test_reference.py` with a small example worked out by hand. To check the
browser against it on any frames folder:

```
uv run tools/browser_check.py FRAMES_FOLDER
```

This runs the page's real code (`web/worker.js`) in headless Chrome and
compares all four images with the Python reference pixel by pixel. Add
`--browser manual` to get a web address to open in Safari or Firefox instead.
It also reports how many frames had a colour label removed.

`tests/test_reference.py` includes a barcode example worked out by hand: five
4 × 3 frames (four solid colours, and one with a marked centre column, a marked
centre row, and grey pixels in the left-hand middle column that must not be
picked). The browser gave the same answers.

On the 3,442 F4 frames (HandBrake frames, labelled with a colour standard),
2026-11-07: Chrome, Firefox, and Safari each matched the Python reference
exactly on all four images (no pixel differed). Making all four took about
18–19 seconds in Chrome and Firefox and 29 in Safari.

**Browsers caching old code.** Browsers keep copies of a page's files. After
the page's code changes, Safari kept using its old copy of `summing.js` with
the new `worker.js`. The worker then couldn't start ("Importing binding name
'BarcodeMaker' is not found"), and the page waited forever with no message.
Two fixes:

- The checking server tells browsers not to cache, and the check page loads
  the page code from a new address each run (`/fresh/<number>/web/...`), so
  every file is fetched fresh.
- The real page now says when its worker can't start and suggests reloading
  or emptying the cache, instead of waiting silently.

While testing the real page locally after changing its code, empty Safari's
cache first (Develop → Empty Caches) or use a Private window. GitHub Pages
lets browsers cache files for only 10 minutes, so published updates reach
students soon, but a student could briefly get a mix of old and new files.
Publishing stamps a version on the code files to prevent that (see
"Publishing the Image maker").

**Checking a stamped copy.** `tests/test_stamp.py` checks the stamping script.
To run a stamped copy in a browser before publishing:

```
python3 tools/stamp_version.py web /tmp/site test
uv run tools/browser_check.py FRAMES_FOLDER --web /tmp/site
```

On the 3,442 F4 frames, 2026-11-09, the stamped copy matched the Python
reference exactly in headless Chrome.

## Publishing the Image maker

GitHub publishes `web/` to <https://briancroxall.github.io/digital_surrealism/>
each time a change to `web/` reaches `main`
(`.github/workflows/pages.yml`). Only `web/` is published, not the extractor,
tests, or tools. The Actions tab on GitHub shows each publish and whether it
worked; it can also be rerun from there ("Run workflow").

**Version stamping.** GitHub Pages lets browsers reuse a file for up to 10
minutes. Without help, a browser could combine a new `worker.js` with a saved
older `summing.js` just after an update, which breaks the page (see "Browsers
caching old code"). So while publishing, `tools/stamp_version.py` adds the
commit ID to every script address in the published copy: `./worker.js`
becomes `./worker.js?v=622036b`. A browser treats a new address as a new file,
so it can't mix in a saved old one. The files in the repo aren't changed. If
any script address is left unstamped, the publish stops with an error and the
old version stays up.

One case is left: a student who loaded the page in the 10 minutes before an
update and uses it just after. The page says it couldn't start and to reload,
and reloading fixes it. To avoid even that, don't push changes to `web/`
during class.

**Updating the published page.** Commit the change to `web/`, push to `main`,
and check the Actions tab. When the run shows a green check, the new version
is published.

**The lab launcher** (`lab/Digital Surrealism.command`) is a short shell
script. Things it does that aren't obvious:

- It adds Homebrew's and uv's folders to the PATH, because programs opened
  from Finder don't get the usual command-line setup.
- It keeps each account's Python and Flask in
  `~/Library/Caches/digital-surrealism/venv` instead of `.venv` in the repo,
  so the repo can sit read-only in `/Users/Shared`. It runs with `--frozen`
  (use `uv.lock` as is, never rewrite it) and `--no-dev` (skip the testing
  tools).
- It finds the repo from its own location, so it must stay in `lab/`; a Finder
  alias works, a copy doesn't (and says so).

Tested on Brian's Mac, 2026-11-09: a fresh, empty home folder with the repo
read-only, and uv made to download its own Python (27 MB): ready in 4 seconds.
Also tested: missing ffmpeg, missing uv, a copied launcher, Control-C, opening
through a Finder alias, and opening it a second time while it's running. Not
tested: a real lab Mac, a student account, or macOS's "unidentified developer"
check.
