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
| Frame extractor (local, lab Macs) | MKV → cropped, square-pixel frames | Command-line core done; web interface next |
| Image maker (browser, GitHub Pages) | frames → summed image + barcodes | Not started |

## Frame extractor

Requires [ffmpeg](https://ffmpeg.org) and [uv](https://docs.astral.sh/uv/).

Find the black bars and save preview images (red box = what will be kept):

```
uv run digital-surrealism detect film.mkv --previews previews/
```

Extract frames:

```
uv run digital-surrealism extract film.mkv frames/
```

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
   the frames are resized to the shape the film actually has on screen.
5. **Scale to DVD size** (default). The *full* frame is scaled so it would
   be 480 pixels tall, then cropped, so a widescreen film comes out shorter
   than 480. A 2.39:1 film is about 853 × 357. A Blu-ray is scaled down by
   the same rule, so every student's frames are comparable. Nothing is
   ever scaled up. With `--full-res`, a Blu-ray keeps its full size (for
   example, 1920 × 804), with folders about 4–5× larger.

Frames are saved as `frame_0001.png`, `frame_0002.png`, … The tool refuses to
write into a folder that already has frames, so two films can't get mixed.

## Development

```
uv run pytest
```

The tests build small synthetic films with ffmpeg (test patterns padded with
black bars, including a dark scene) and check crop detection, frame sizes, and
frame counts.
