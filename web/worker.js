// Reads frames one at a time in the background, so the page stays responsive.
//
// Receives: {files: [File or Blob, ...], names: [string, ...]} in frame order.
// Sends:    {type: "progress", done, total}
//           {type: "done", images: {summed, horizontal, vertical, average} (PNG Blobs),
//            width, height, count, ranges, labelled}
//           {type: "error", message}

import {withoutColourLabels} from "./png.js";
import {BarcodeMaker, FrameSummer} from "./summing.js";

async function readPixels(file, canvasCache, labelled) {
  // Ask for the file's exact pixel values, with no colour adjustment. Safari
  // adjusts colours anyway if the PNG has a colour label, so remove it first.
  const original = new Uint8Array(await file.arrayBuffer());
  const bytes = withoutColourLabels(original);
  if (bytes !== original) labelled.count += 1;
  const bitmap = await createImageBitmap(new Blob([bytes], {type: "image/png"}), {
    colorSpaceConversion: "none",
    premultiplyAlpha: "none",
  });
  let {canvas, context} = canvasCache;
  if (!canvas || canvas.width !== bitmap.width || canvas.height !== bitmap.height) {
    canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
    context = canvas.getContext("2d", {willReadFrequently: true});
    Object.assign(canvasCache, {canvas, context});
  }
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.drawImage(bitmap, 0, 0);
  bitmap.close();
  return context.getImageData(0, 0, canvas.width, canvas.height);
}

async function toPng({pixels, width, height}) {
  const canvas = new OffscreenCanvas(width, height);
  canvas.getContext("2d").putImageData(new ImageData(pixels, width, height), 0, 0);
  return canvas.convertToBlob({type: "image/png"});
}

self.onmessage = async ({data: {files, names}}) => {
  try {
    const summer = new FrameSummer();
    const barcodes = new BarcodeMaker();
    const canvasCache = {};
    const labelled = {count: 0};  // frames whose colour label was removed
    for (let i = 0; i < files.length; i++) {
      let image;
      try {
        image = await readPixels(files[i], canvasCache, labelled);
      } catch {
        throw new Error(`Couldn't read ${names[i]} as an image.`);
      }
      summer.add(image, names[i]);  // checks the size first
      barcodes.add(image);
      if (i % 20 === 0 || i === files.length - 1) {
        self.postMessage({type: "progress", done: i + 1, total: files.length});
      }
    }
    const result = summer.summed();
    const images = {
      summed: await toPng(result),
      horizontal: await toPng(barcodes.horizontal()),
      vertical: await toPng(barcodes.vertical()),
      average: await toPng(barcodes.average()),
    };
    self.postMessage({
      type: "done", images, width: result.width, height: result.height,
      count: summer.count, ranges: result.ranges, labelled: labelled.count,
    });
  } catch (error) {
    self.postMessage({type: "error", message: error.message});
  }
};
