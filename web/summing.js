// The summed image: the average of all frames, with each colour channel
// stretched so its darkest value becomes 0 and its brightest 255.
//
// This is the net effect of the ImageMagick recipe used in past semesters
// (see README, "The summed image"): -evaluate-sequence Mean, then
// -auto-level on each channel separately.

export class FrameSummer {
  constructor() {
    this.width = null;
    this.height = null;
    this.count = 0;
    this.totals = null; // running total of R, G, B for every pixel
  }

  // Add one frame. `image` is an ImageData (RGBA bytes, alpha ignored).
  add(image, name = "") {
    if (this.totals === null) {
      this.width = image.width;
      this.height = image.height;
      this.totals = new Float64Array(image.width * image.height * 3);
    } else if (image.width !== this.width || image.height !== this.height) {
      throw new Error(
        `${name} is ${image.width} × ${image.height}, but the frames before it are ` +
        `${this.width} × ${this.height}. All frames must be the same size; ` +
        `is this folder mixing frames from different films?`);
    }
    const data = image.data;
    const totals = this.totals;
    for (let pixel = 0, i = 0; i < data.length; i += 4, pixel += 3) {
      totals[pixel] += data[i];
      totals[pixel + 1] += data[i + 1];
      totals[pixel + 2] += data[i + 2];
    }
    this.count += 1;
  }

  // The average frame, as floating-point R, G, B values (0–255).
  mean() {
    return this.totals.map((total) => total / this.count);
  }

  // The finished summed image as RGBA bytes, plus the ranges that were
  // stretched (useful for explaining the result).
  summed() {
    const mean = this.mean();
    const ranges = [0, 1, 2].map((channel) => {
      let low = Infinity, high = -Infinity;
      for (let i = channel; i < mean.length; i += 3) {
        if (mean[i] < low) low = mean[i];
        if (mean[i] > high) high = mean[i];
      }
      return {low, high};
    });
    const pixels = new Uint8ClampedArray(this.width * this.height * 4);
    for (let pixel = 0, i = 0; pixel < mean.length; pixel += 3, i += 4) {
      for (let channel = 0; channel < 3; channel++) {
        const {low, high} = ranges[channel];
        const value = mean[pixel + channel];
        // A perfectly flat channel can't be stretched; keep it as it is.
        const stretched = high > low ? (value - low) / (high - low) * 255 : value;
        pixels[i + channel] = Math.floor(stretched + 0.5);
      }
      pixels[i + 3] = 255;
    }
    return {pixels, width: this.width, height: this.height, ranges};
  }
}

// The three barcodes, one stripe per frame in film order. Not stretched: they
// show the frames' own colours.
//   horizontal: each frame's centre column, side by side  (frames × height)
//   vertical:   each frame's centre row, stacked          (width × frames)
//   average:    each frame's average colour as a stripe   (frames × height)
// "Centre" with an even size is the right-hand (or lower) of the two middle
// columns (rows): column 361 of 720, counting from 1. With an odd size it's
// the true middle: column 427 of 853.
export class BarcodeMaker {
  constructor() {
    this.columns = [];  // centre column of each frame: height × RGB
    this.rows = [];     // centre row of each frame: width × RGB
    this.averages = []; // average colour of each frame: [R, G, B]
  }

  // Add one frame (ImageData). FrameSummer.add has already checked its size.
  add(image) {
    const {width, height, data} = image;
    this.width = width;
    this.height = height;
    const centreX = Math.floor(width / 2);
    const centreY = Math.floor(height / 2);

    const column = new Uint8Array(height * 3);
    for (let y = 0; y < height; y++) {
      const i = (y * width + centreX) * 4;
      column.set(data.subarray(i, i + 3), y * 3);
    }
    const row = new Uint8Array(width * 3);
    for (let x = 0; x < width; x++) {
      const i = (centreY * width + x) * 4;
      row.set(data.subarray(i, i + 3), x * 3);
    }
    const sums = [0, 0, 0];
    for (let i = 0; i < data.length; i += 4) {
      sums[0] += data[i];
      sums[1] += data[i + 1];
      sums[2] += data[i + 2];
    }
    this.columns.push(column);
    this.rows.push(row);
    this.averages.push(sums.map((sum) => sum / (width * height)));
  }

  // Each barcode as {pixels (RGBA bytes), width, height}.
  horizontal() {
    const frames = this.columns.length, height = this.height;
    const pixels = new Uint8ClampedArray(frames * height * 4);
    this.columns.forEach((column, x) => {
      for (let y = 0; y < height; y++) {
        const i = (y * frames + x) * 4;
        pixels.set(column.subarray(y * 3, y * 3 + 3), i);
        pixels[i + 3] = 255;
      }
    });
    return {pixels, width: frames, height};
  }

  vertical() {
    const frames = this.rows.length, width = this.width;
    const pixels = new Uint8ClampedArray(width * frames * 4);
    this.rows.forEach((row, y) => {
      for (let x = 0; x < width; x++) {
        const i = (y * width + x) * 4;
        pixels.set(row.subarray(x * 3, x * 3 + 3), i);
        pixels[i + 3] = 255;
      }
    });
    return {pixels, width, height: frames};
  }

  average() {
    const frames = this.averages.length, height = this.height;
    const pixels = new Uint8ClampedArray(frames * height * 4);
    this.averages.forEach((colour, x) => {
      const rounded = colour.map((value) => Math.floor(value + 0.5));
      for (let y = 0; y < height; y++) {
        const i = (y * frames + x) * 4;
        pixels[i] = rounded[0];
        pixels[i + 1] = rounded[1];
        pixels[i + 2] = rounded[2];
        pixels[i + 3] = 255;
      }
    });
    return {pixels, width: frames, height};
  }
}

// Sort filenames the way people expect: frame_2 before frame_10.
export function byFrameOrder(a, b) {
  return a.localeCompare(b, undefined, {numeric: true});
}
