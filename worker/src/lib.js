// Pure helpers for the quote form Worker. No Cloudflare imports, so they can be tested in Node.

export const LIMITS = {
  maxFiles: 8,
  maxFileBytes: 10 * 1024 * 1024,
  maxTotalBytes: 30 * 1024 * 1024,
  maxRequestBytes: 32 * 1024 * 1024,
  maxMessage: 5000,
  maxShort: 200,
};

const HEIC_BRANDS = new Set(["heic", "heix", "hevc", "hevx", "heim", "heis", "mif1", "msf1"]);
const ascii = (b, start, len) => String.fromCharCode(...b.slice(start, start + len));

// Identify an image from its first bytes. The browser-declared type is never trusted.
export function sniffImage(b) {
  if (b.length >= 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return { type: "image/jpeg", ext: "jpg" };
  if (b.length >= 8 && b[0] === 0x89 && ascii(b, 1, 3) === "PNG" && b[4] === 0x0d && b[5] === 0x0a && b[6] === 0x1a && b[7] === 0x0a)
    return { type: "image/png", ext: "png" };
  if (b.length >= 12 && ascii(b, 0, 4) === "RIFF" && ascii(b, 8, 4) === "WEBP") return { type: "image/webp", ext: "webp" };
  if (b.length >= 12 && ascii(b, 4, 4) === "ftyp" && HEIC_BRANDS.has(ascii(b, 8, 4))) return { type: "image/heic", ext: "heic" };
  return null;
}

// A declared type must be an image type (or empty, which some browsers send for .heic).
export function declaredTypeOk(t) {
  return t === "" || /^image\/(jpeg|png|webp|heic|heif)$/i.test(t);
}

// Trim, strip control characters (keeping newlines only when allowed) and cap the length.
export function cleanText(value, max, { multiline = false } = {}) {
  if (typeof value !== "string") return "";
  const re = multiline ? /[\u0000-\u0009\u000b\u000c\u000e-\u001f\u007f]/g : /[\u0000-\u001f\u007f]/g;
  return value.replace(/\r\n?/g, "\n").replace(re, " ").trim().slice(0, max);
}

// Deliberately strict: no whitespace, quotes, angle brackets or commas, so it is safe in a header.
export function validEmail(s) {
  return s.length <= 254 && /^[^\s@<>()",;:\\]+@[^\s@<>()",;:\\]+\.[^\s@<>()",;:\\]+$/.test(s);
}

const enc = new TextEncoder();
const toHex = (buf) => [...new Uint8Array(buf)].map((x) => x.toString(16).padStart(2, "0")).join("");
const fromHex = (h) => {
  if (!/^[0-9a-f]+$/i.test(h) || h.length % 2) return null;
  return new Uint8Array(h.match(/../g).map((x) => parseInt(x, 16)));
};
const hmacKey = (secret, usages) =>
  crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, usages);

export async function sign(secret, data) {
  return toHex(await crypto.subtle.sign("HMAC", await hmacKey(secret, ["sign"]), enc.encode(data)));
}

// crypto.subtle.verify compares in constant time.
export async function verify(secret, data, sigHex) {
  const sig = fromHex(sigHex || "");
  if (!sig) return false;
  return crypto.subtle.verify("HMAC", await hmacKey(secret, ["verify"]), sig, enc.encode(data));
}
