module.exports = {
  name: "3DScanPost",
  url: "https://3dscanpost.com",
  description: "Professional 3D scanning service for hobbyists and small businesses. Mail us your parts, get high-quality STL or PLY scan files back.",
  ogImage: "https://3dscanpost.com/assets/images/og-image.jpg",
  // Cloudflare Turnstile site key. Local dev (NODE_ENV=dev) uses Cloudflare's always-pass test key,
  // because the real widget only works on 3dscanpost.com.
  turnstileSiteKey: process.env.NODE_ENV === "dev" ? "1x00000000000000000000AA" : "0x4AAAAAAGPzkPYaisPLU4-T",
  logo: "https://3dscanpost.com/assets/images/logo.png",
  author: "Mike"
};
