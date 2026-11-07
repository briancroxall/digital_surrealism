# digital_surrealism

Tools for students in *Introduction to Digital Humanities* to make "digital
surrealism" images of a film, following Kevin L. Ferguson, ["Digital
Surrealism: Visualizing Walt Disney Animation Studios"](https://dhq.digitalhumanities.org/vol/11/1/000276/000276.html)
(*DHQ* 11.1, 2017).

Students start with an MKV ripped by MakeMKV and end with:

- a folder of frames (one every 2 seconds)
- a summed image of all the frames
- three barcodes (center-column slice, center-row slice, average color)

## Status

| Part | What it does | Status |
|---|---|---|
| Frame extractor (local, lab Macs) | MKV → cropped, square-pixel frames | Command line and web interface done; lab launcher next |
| Image maker (browser, GitHub Pages) | frames → summed image + barcodes | Summed image done; barcodes and saving next |

## Frame extractor

Requires [ffmpeg](https://ffmpeg.org) and [uv](https://docs.astral.sh/uv/).
Runs on macOS.

### In the browser (for students)

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

A web page (`web/`) that turns a folder of frames into a summed image (and,
soon, barcodes). Everything happens in the browser on the student's own
computer; no frames are uploaded. It will be published on GitHub Pages. Until
then, run it locally:

```
uv run python -m http.server 8000 -d web -b 127.0.0.1
```

then open <http://127.0.0.1:8000>. (Opening `index.html` straight from Finder
doesn't work: browsers only run the page's background worker from a web
address.) Press Control-C to stop the server.

Choose the frames folder, then click **Make summed image**. The page uses
every PNG in the folder, sorted by number (`frame_2` before `frame_10`), and
stops with a message if the frames aren't all the same size.

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
compares the result pixel by pixel. Add `--browser manual` to get a web address
to open in Safari or Firefox instead. On the 3,442 F4 frames (HandBrake
frames, labelled with a colour standard), Chrome, Firefox, and Safari each
matched the Python reference exactly (no pixel differed). Reading and summing
took about 14 seconds in Chrome and Firefox and 27 in Safari. The script also
reports how many frames had a colour label removed.

The checking server tells browsers not to cache, and the check page loads the
worker from a new address each run, because Safari otherwise kept running an
old cached copy of `web/worker.js` after it was changed. The same can happen
with the real page while testing locally: in Safari, use Develop → Empty
Caches (or a Private window) after changing the page's code. GitHub Pages lets
browsers cache files for only 10 minutes, so students will get updates soon
after they're published.
