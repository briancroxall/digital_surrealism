// Remove colour labels from a PNG so every browser reads its stored numbers.
//
// A PNG can say which colour standard its numbers are in (for example, NTSC
// video). Chrome and Firefox ignore that when asked to, but Safari converts the
// colours to its own standard anyway, which shifts the numbers by a few points
// and changes the summed image. The frames are data, so we drop the labels
// before decoding (from the in-memory copy only; files on disk are untouched).
// See README, "Why the Image maker ignores colour labels".

const COLOUR_LABELS = new Set(["cICP", "cHRM", "gAMA", "iCCP", "sRGB", "mDCV", "cLLI"]);
const SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10];

// Takes the bytes of a PNG file; returns them without colour-label chunks.
// Anything that isn't a PNG is returned unchanged.
export function withoutColourLabels(bytes) {
  if (bytes.length < 8 || SIGNATURE.some((value, i) => bytes[i] !== value)) return bytes;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const kept = [bytes.subarray(0, 8)];
  let removed = false;
  let position = 8;
  while (position + 8 <= bytes.length) {
    // Each chunk: 4-byte length, 4-byte type, data, 4-byte checksum.
    const length = view.getUint32(position);
    const type = String.fromCharCode(...bytes.subarray(position + 4, position + 8));
    const end = position + 12 + length;
    if (COLOUR_LABELS.has(type)) {
      removed = true;
    } else {
      kept.push(bytes.subarray(position, end));
    }
    position = end;
  }
  if (!removed) return bytes;
  const out = new Uint8Array(kept.reduce((sum, part) => sum + part.length, 0));
  let offset = 0;
  for (const part of kept) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}
