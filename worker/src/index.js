// Quote form handler for 3dscanpost.com.
// POST /api/quote            multipart form -> Turnstile, validation, R2, notification + confirmation via Resend
// GET  /api/quote/files/...  signed, expiring links to the stored photos (the bucket stays private)

import { LIMITS, sniffImage, declaredTypeOk, cleanText, validEmail, sign, verify } from "./lib.js";

const LINK_TTL_SECONDS = 30 * 24 * 3600;
const FILE_KEY = /^\d{8}-[0-9a-f-]{36}\/\d+\.(jpg|png|webp|heic)$/;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/api/quote" && request.method === "POST") return submit(request, env, ctx);
    if (url.pathname.startsWith("/api/quote/files/") && request.method === "GET") return serveFile(url, env);
    return new Response("Not found", { status: 404 });
  },
};

// ---------- responses ----------

function respond(wantsJson, env, status, message) {
  if (wantsJson) return Response.json(status < 300 ? { ok: true } : { ok: false, error: message }, { status });
  if (status < 300) return Response.redirect(`${env.PUBLIC_BASE}/thanks/`, 303);
  const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Request not sent</title><body style="font-family:system-ui;max-width:32rem;margin:4rem auto;padding:0 1rem"><h1>Request not sent</h1><p>${message}</p><p><a href="${env.PUBLIC_BASE}/#contact">Back to the form</a></p>`;
  return new Response(html, { status, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

// ---------- submit ----------

async function submit(request, env, ctx) {
  const wantsJson = (request.headers.get("Accept") || "").includes("application/json");
  const fail = (status, message) => respond(wantsJson, env, status, message);

  // Cheap checks before reading the body.
  const origin = request.headers.get("Origin");
  if (origin && origin !== env.PUBLIC_BASE) return fail(403, "Request not allowed.");
  if (!(request.headers.get("Content-Type") || "").startsWith("multipart/form-data")) return fail(415, "Unsupported form encoding.");
  if (Number(request.headers.get("Content-Length") || 0) > LIMITS.maxRequestBytes) return fail(413, "Those photos are too large. Please send fewer or smaller photos.");

  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const { success: allowed } = await env.RATE_LIMITER.limit({ key: ip });
  if (!allowed) return fail(429, "Too many requests. Please wait a minute and try again.");

  let form;
  try {
    form = await request.formData();
  } catch {
    return fail(400, "That form could not be read.");
  }

  // Bots fill the hidden field. Pretend it worked.
  if (form.get("_gotcha")) return respond(wantsJson, env, 200);

  // Turnstile comes first: nothing is stored or sent until it passes.
  const token = form.get("cf-turnstile-response");
  if (typeof token !== "string" || !token || !(await turnstileOk(token, ip, env))) {
    return fail(400, "The spam check did not pass. Please reload the page and try again.");
  }

  const name = cleanText(form.get("name"), LIMITS.maxShort);
  const email = cleanText(form.get("email"), 254);
  const message = cleanText(form.get("message"), LIMITS.maxMessage, { multiline: true });
  if (!name || !message || !validEmail(email)) return fail(400, "Please fill in your name, a valid email address and a message.");

  if (form.get("agree") !== "yes") return fail(400, "Please confirm that you agree to the service disclaimer.");

  const details = {
    country: cleanText(form.get("country"), LIMITS.maxShort),
    dimensions: cleanText(form.get("dimensions"), LIMITS.maxShort),
    material: cleanText(form.get("material"), LIMITS.maxShort),
    turnaround: cleanText(form.get("turnaround"), LIMITS.maxShort),
  };

  // Photos: count, per-file and total size, declared type, then the real type from the bytes.
  const files = form.getAll("photos").filter((f) => typeof f !== "string" && f.size > 0);
  if (files.length > LIMITS.maxFiles) return fail(400, `Please send at most ${LIMITS.maxFiles} photos.`);
  let total = 0;
  const photos = [];
  for (const f of files) {
    total += f.size;
    if (f.size > LIMITS.maxFileBytes) return fail(413, "One of the photos is over 10 MB.");
    if (total > LIMITS.maxTotalBytes) return fail(413, "The photos are over 30 MB in total.");
    if (!declaredTypeOk(f.type)) return fail(400, "Only image files can be attached.");
    const sniffed = sniffImage(new Uint8Array(await f.slice(0, 16).arrayBuffer()));
    if (!sniffed) return fail(400, "Only JPEG, PNG, WebP or HEIC photos can be attached.");
    photos.push({ file: f, ...sniffed, original: cleanText(f.name, 120) });
  }

  // Store everything under one prefix per submission. File names are generated, never user-supplied.
  const id = `${new Date().toISOString().slice(0, 10).replaceAll("-", "")}-${crypto.randomUUID()}`;
  const stored = [];
  try {
    for (const [i, p] of photos.entries()) {
      const key = `${id}/${i + 1}.${p.ext}`;
      await env.PHOTOS.put(key, await p.file.arrayBuffer(), {
        httpMetadata: { contentType: p.type },
        customMetadata: { originalName: p.original },
      });
      stored.push({ key, original: p.original, size: p.file.size });
    }
    const record = { id, receivedAt: new Date().toISOString(), name, email, ...details, agreedToDisclaimer: true, message, photos: stored };
    await env.PHOTOS.put(`${id}/submission.json`, JSON.stringify(record, null, 2), { httpMetadata: { contentType: "application/json" } });
  } catch (err) {
    console.error("R2 write failed", id, err);
    return fail(500, "Something went wrong saving your request. Please email us instead.");
  }

  // Signed links, valid for 30 days.
  const exp = Math.floor(Date.now() / 1000) + LINK_TTL_SECONDS;
  const links = [];
  for (const s of stored) {
    const sig = await sign(env.LINK_SECRET, `${s.key}.${exp}`);
    links.push(`${env.PUBLIC_BASE}/api/quote/files/${s.key}?exp=${exp}&sig=${sig}`);
  }

  // Notification to the owner. If this fails nobody would ever see the request, so tell the visitor.
  const text = [
    `New quote request ${id}`,
    "",
    `Name: ${name}`,
    `Email: ${email}`,
    `Country: ${details.country || "-"}`,
    `Dimensions: ${details.dimensions || "-"}`,
    `Material: ${details.material || "-"}`,
    `Turnaround: ${details.turnaround || "-"}`,
    "",
    "Message:",
    message,
    "",
    stored.length ? `Photos (${stored.length}, links expire in 30 days):` : "No photos attached.",
    ...links.map((l, i) => `${i + 1}. ${stored[i].original || "photo"}  ${l}`),
  ].join("\n");

  try {
    await sendEmail(env, {
      from: env.NOTIFY_FROM,
      to: [env.NOTIFY_TO],
      reply_to: email,
      subject: `New quote request ${id.slice(9, 17)}`,
      text,
    });
  } catch (err) {
    console.error("Notification email failed", id, err);
    return fail(500, "Something went wrong sending your request. Please email us instead.");
  }

  // Fixed-text confirmation. A failure here is logged but doesn't fail the request.
  ctx.waitUntil(sendConfirmation(email, env));

  return respond(wantsJson, env, 200);
}

async function turnstileOk(token, ip, env) {
  try {
    const body = new FormData();
    body.append("secret", env.TURNSTILE_SECRET);
    body.append("response", token);
    body.append("remoteip", ip);
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body });
    const out = await r.json();
    if (out.success !== true) return false;
    // Skipped only in local dev, where Turnstile's test keys report a dummy hostname.
    return env.TURNSTILE_CHECK_HOSTNAME === "false" || out.hostname === new URL(env.PUBLIC_BASE).hostname;
  } catch (err) {
    console.error("Turnstile verification failed", err);
    return false;
  }
}

// The text is fixed. Only the recipient address comes from the submitter.
async function sendConfirmation(to, env) {
  try {
    await sendEmail(env, {
      from: env.CONFIRM_FROM,
      to: [to],
      reply_to: env.REPLY_TO,
      subject: "We received your 3D scanning request",
      text: "Thanks for your request. We have received it and will reply with a quote, usually within 24 hours.\n\n3DScanPost\nhttps://3dscanpost.com",
    });
  } catch (err) {
    console.error("Confirmation email failed", err);
  }
}

// One place that talks to Resend. In local dev (DEV_LOG_EMAILS=true) it prints the email instead.
async function sendEmail(env, message) {
  if (env.DEV_LOG_EMAILS === "true") {
    console.log("[dev] email not sent:\n" + JSON.stringify(message, null, 2));
    return;
  }
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify(message),
  });
  if (!r.ok) throw new Error(`Resend ${r.status}: ${await r.text()}`);
}

// ---------- signed photo links ----------

async function serveFile(url, env) {
  const key = decodeURIComponent(url.pathname.slice("/api/quote/files/".length));
  const exp = Number(url.searchParams.get("exp"));
  if (!FILE_KEY.test(key) || !Number.isFinite(exp) || exp < Date.now() / 1000) return new Response("Not found", { status: 404 });
  if (!(await verify(env.LINK_SECRET, `${key}.${exp}`, url.searchParams.get("sig")))) return new Response("Not found", { status: 404 });

  const obj = await env.PHOTOS.get(key);
  if (!obj) return new Response("Not found", { status: 404 });
  return new Response(obj.body, {
    headers: {
      "Content-Type": obj.httpMetadata?.contentType || "application/octet-stream",
      "Content-Disposition": "inline",
      "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": "default-src 'none'; sandbox",
      "Cache-Control": "private, no-store",
      "X-Robots-Tag": "noindex",
    },
  });
}
