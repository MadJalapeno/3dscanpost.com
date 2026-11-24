import assert from "node:assert/strict";
import { sniffImage, declaredTypeOk, cleanText, validEmail, sign, verify } from "../src/lib.js";

const b = (...x) => Uint8Array.from(x);
const str = (s) => [...s].map((c) => c.charCodeAt(0));

// magic bytes
assert.equal(sniffImage(b(0xff, 0xd8, 0xff, 0xe0)).type, "image/jpeg");
assert.equal(sniffImage(b(0x89, ...str("PNG"), 0x0d, 0x0a, 0x1a, 0x0a)).type, "image/png");
assert.equal(sniffImage(b(...str("RIFF"), 0, 0, 0, 0, ...str("WEBP"))).type, "image/webp");
assert.equal(sniffImage(b(0, 0, 0, 24, ...str("ftypheic"))).type, "image/heic");
assert.equal(sniffImage(b(0, 0, 0, 24, ...str("ftypmp42"))), null); // video, not an image
assert.equal(sniffImage(b(...str("<svg xmlns=\"http\"><script>"))), null); // SVG rejected
assert.equal(sniffImage(b(...str("<html>"))), null);
assert.equal(sniffImage(b()), null);

// declared types
assert.ok(declaredTypeOk("image/jpeg") && declaredTypeOk("") && declaredTypeOk("image/heic"));
assert.ok(!declaredTypeOk("application/pdf") && !declaredTypeOk("image/svg+xml") && !declaredTypeOk("text/html"));

// text cleaning
assert.equal(cleanText("  Bob\r\nBcc: x@y.z ", 50), "Bob Bcc: x@y.z");
assert.equal(cleanText("a\nb\u0000c", 50, { multiline: true }), "a\nb c");
assert.equal(cleanText("x".repeat(500), 10).length, 10);
assert.equal(cleanText(42, 10), "");

// emails (header injection attempts must fail)
assert.ok(validEmail("a.b+c@example.co.uk"));
for (const bad of ["a@b", "a b@c.de", "a@b.de\r\nBcc: evil@x.com", "<a@b.de>", "a@b.de, c@d.de", "@b.de", "a@b.de\n"]) assert.ok(!validEmail(bad), bad);

// signing
const sig = await sign("secret", "20261123-x/1.jpg.1800000000");
assert.ok(await verify("secret", "20261123-x/1.jpg.1800000000", sig));
assert.ok(!(await verify("secret", "20261123-x/2.jpg.1800000000", sig)));
assert.ok(!(await verify("other", "20261123-x/1.jpg.1800000000", sig)));
assert.ok(!(await verify("secret", "x", "zz")));
assert.ok(!(await verify("secret", "x", undefined)));

console.log("lib tests passed");
