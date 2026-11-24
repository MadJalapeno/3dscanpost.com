# Quote form Worker: setup

The form on 3dscanpost.com posts to `/api/quote`. This Worker checks Turnstile, validates the photos, stores them in a private R2 bucket, and sends two emails through Resend: the notification to `contact@3dscanpost.com` and a fixed-text confirmation to the submitter.

Email Routing and the `send_email` binding are not used. 3dscanpost.com's mail is hosted at Fastmail, so its MX records must stay as they are.

## 1. Cloudflare resources

```sh
cd worker
npm install
npx wrangler login

# Private bucket for photos and a JSON copy of every submission
npx wrangler r2 bucket create 3dscanpost-quote-photos

# Optional: delete submissions after 90 days (check `wrangler r2 bucket lifecycle --help` for the exact syntax)
npx wrangler r2 bucket lifecycle add 3dscanpost-quote-photos delete-after-90d --expire-days 90
```

## 2. Turnstile

1. Dashboard, then **Turnstile**, then **Add widget** for `3dscanpost.com`. Mode: Managed.
2. Put the **site key** in `src/_data/site.js` (`turnstileSiteKey`). Local dev uses Cloudflare's always-pass test key automatically.
3. Store the **secret key** as a Worker secret (step 5).

## 3. Resend (both emails)

1. Add a sending domain in Resend. Use a subdomain such as `send.3dscanpost.com`, so its records don't clash with your Fastmail records on the root domain.
2. Add the DNS records Resend shows you (see the table below).
3. Create an API key with **sending access only**.

## 4. Secrets and deploy

```sh
npx wrangler secret put TURNSTILE_SECRET   # Turnstile secret key
npx wrangler secret put RESEND_API_KEY     # Resend key
npx wrangler secret put LINK_SECRET        # run `openssl rand -hex 32` and paste the result
npx wrangler deploy
```

The route `3dscanpost.com/api/quote*` is in `wrangler.toml`. It takes priority over the static site for those paths only.

## DNS records

| Purpose | Type | Name | Value |
|---|---|---|---|
| Existing mail (Fastmail) | MX, TXT | root | Leave alone. Do not enable Cloudflare Email Routing on this domain. |
| Resend bounce/SPF | MX | `send` | The value Resend shows (an `amazonses.com` feedback host), priority 10 |
| Resend SPF | TXT | `send` | `v=spf1 include:amazonses.com ~all` (copy the exact value Resend shows) |
| Resend DKIM | TXT | `resend._domainkey` | The long `p=...` public key Resend shows |
| DMARC | TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:YOU@example.com; adkim=r; aspf=r` |

Use Resend's own values for the `send` and `resend._domainkey` rows, since they are specific to your account. Don't publish two SPF records on the same name. Each name gets exactly one `v=spf1` record.

DMARC: start with `p=none` and read the reports for a few weeks. Once your mail passes SPF and DKIM consistently, move to `p=quarantine`, then `p=reject`.

## Checks before you rely on it

- Submit the live form with and without photos. Confirm that the notification arrives at contact@3dscanpost.com, that the photo links open, and that the confirmation reaches a non-Gmail address too.
- A submission that fails to email you returns an error to the visitor, which tells them to email you directly.
- Photo links are signed and expire after 30 days. You can still browse the bucket in the dashboard afterwards, and each submission has a `submission.json` copy.
- Confirmation emails go to whatever address is typed in the form, so the Turnstile check and rate limit are what stop someone using the form to send mail to other people. `RATE_LIMITER` allows 4 posts per minute per IP per location. Tighten it in `wrangler.toml` if you see abuse.
- Add a line about storing photos and form details to a privacy page when you have one.

## Local testing

```sh
cd worker
# .dev.vars (gitignored) holds Turnstile's test secret, and DEV_LOG_EMAILS=true prints emails instead of sending
npm run dev          # http://localhost:8787
npm test             # unit tests for the validation helpers
```
