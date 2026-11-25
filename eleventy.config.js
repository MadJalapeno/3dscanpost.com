const now = new Date();

// Import 11ty plugins
import eleventyNavigationPlugin from "@11ty/eleventy-navigation";
import http from "node:http";
import { execSync } from "node:child_process";
import Image from "@11ty/eleventy-img";
import { openSync, readSync, closeSync } from "node:fs";

// Width and height of a PNG, read from its header (bytes 16-24). Null for anything else.
function pngSize(file) {
  try {
    const fd = openSync(file, "r");
    const buf = Buffer.alloc(24);
    readSync(fd, buf, 0, 24, 0);
    closeSync(fd);
    if (buf.toString("ascii", 1, 4) !== "PNG") return null;
    return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  } catch {
    return null;
  }
}

export default function (eleventyConfig) {
  eleventyConfig.setInputDirectory("src");
  eleventyConfig.setIncludesDirectory("_includes");
  eleventyConfig.setLayoutsDirectory("_layouts");

  eleventyConfig.addPassthroughCopy("src/assets/scans/");
  eleventyConfig.addPassthroughCopy("src/assets/images/");
  eleventyConfig.addPassthroughCopy("src/assets/js/");
  eleventyConfig.addPassthroughCopy("src/assets/fonts/");
  // three.js for the Examples page, self-hosted so ad/tracker blockers can't break it
  eleventyConfig.addPassthroughCopy({
    "node_modules/three/build/three.module.min.js": "assets/vendor/three-0.160.0/build/three.module.min.js",
    "node_modules/three/examples/jsm/loaders/GLTFLoader.js": "assets/vendor/three-0.160.0/examples/jsm/loaders/GLTFLoader.js",
    "node_modules/three/examples/jsm/loaders/DRACOLoader.js": "assets/vendor/three-0.160.0/examples/jsm/loaders/DRACOLoader.js",
    "node_modules/three/examples/jsm/controls/OrbitControls.js": "assets/vendor/three-0.160.0/examples/jsm/controls/OrbitControls.js",
    "node_modules/three/examples/jsm/utils/BufferGeometryUtils.js": "assets/vendor/three-0.160.0/examples/jsm/utils/BufferGeometryUtils.js",
    "node_modules/three/examples/jsm/libs/draco/gltf": "assets/vendor/three-0.160.0/examples/jsm/libs/draco/gltf",
  });
  eleventyConfig.addPassthroughCopy({ "src/downloads/stl_align.py": "stl-align/stl_align.py" });
  // Sample deviation report for 3D Mesh Compare, served as a static page rather than a template
  eleventyConfig.ignores.add("src/demo*_report.html");
  eleventyConfig.addPassthroughCopy({ "src/demo002_remote_aligned_deviation_report.html": "tools/demo-report/index.html" });
  eleventyConfig.addPassthroughCopy("src/robots.txt");
  eleventyConfig.addPassthroughCopy("src/manifest.webmanifest");
  eleventyConfig.addPassthroughCopy("src/_headers");
  eleventyConfig.addPassthroughCopy("src/_redirects");

  eleventyConfig.addWatchTarget("src");
  eleventyConfig.setServerOptions({
    liveReload: true,
    // Local dev only: forward the quote form to the Worker (`cd worker && npm run dev`, port 8787).
    middleware: [
      (req, res, next) => {
        if (!req.url.startsWith("/api/quote")) return next();
        // Read the whole request first, so an early rejection can't cut the upload off mid-way.
        const chunks = [];
        req.on("data", (c) => chunks.push(c));
        req.on("end", () => {
          const body = Buffer.concat(chunks);
          const headers = { ...req.headers, host: "localhost:8787", "content-length": body.length };
          delete headers.connection;
          delete headers["transfer-encoding"];
          const upstream = http.request({ host: "localhost", port: 8787, path: req.url, method: req.method, headers }, (r) => {
            const out = { ...r.headers };
            delete out.connection;
            delete out["transfer-encoding"];
            res.writeHead(r.statusCode, out);
            r.pipe(res);
          });
          upstream.on("error", () => {
            res.writeHead(502, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ ok: false, error: "The local form Worker is not running. Start it with: cd worker && npm run dev" }));
          });
          upstream.end(body);
        });
      },
    ],
  });

  // read data from .env file to determine dev or prod
  eleventyConfig.addGlobalData("env", process.env.ELEVENTY_ENV);

  // 11ty Plugins
  eleventyConfig.addPlugin(eleventyNavigationPlugin);

  // Give local markdown images width/height and lazy loading so the page doesn't jump as they load.
  eleventyConfig.amendLibrary("md", (mdLib) => {
    const defaultImage = mdLib.renderer.rules.image || ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options));
    mdLib.renderer.rules.image = (tokens, idx, options, env, self) => {
      const token = tokens[idx];
      const src = token.attrGet("src") || "";
      if (src.startsWith("/assets/images/")) {
        const size = pngSize(`src${src}`);
        if (size) {
          token.attrSet("width", String(size.width));
          token.attrSet("height", String(size.height));
        }
        token.attrSet("loading", "lazy");
        token.attrSet("decoding", "async");
      }
      return defaultImage(tokens, idx, options, env, self);
    };
  });

  // Screenshot thumbnail that opens the full-size image in the modal (see default.njk).
  // Sources live in ./screenshots; output is resized WebP in _site/assets/images/screenshots.
  eleventyConfig.addAsyncShortcode("shot", async function (file, alt, caption = "", cls = "", eager = false) {
    const meta = await Image(`screenshots/${file}`, {
      widths: [640, 1800],
      formats: ["webp"],
      outputDir: "_site/assets/images/screenshots/",
      urlPath: "/assets/images/screenshots/",
    });
    const [thumb, full = thumb] = meta.webp;
    const figcaption = caption ? `<figcaption class="mt-2 font-mono text-xs opacity-70">${caption}</figcaption>` : "";
    return `<figure class="not-prose m-0 ${cls}"><a href="${full.url}" data-modal data-caption="${caption || alt}" class="block overflow-hidden rounded-box border border-base-content/15 bg-base-100 transition-colors hover:border-primary motion-reduce:transition-none"><img src="${thumb.url}" width="${thumb.width}" height="${thumb.height}" alt="${alt}" ${eager ? 'fetchpriority="high"' : 'loading="lazy"'} class="h-auto w-full object-contain"></a>${figcaption}</figure>`;
  });

  // Global data
  eleventyConfig.addGlobalData("buildTime", now);

  // Shortcodes
  eleventyConfig.addShortcode('version', function () {
    return String(now.getTime())
  });
  eleventyConfig.addShortcode('year', function () {
    return now.getFullYear()
  });

  // Filters
  // Last git commit date of a source file. Returns "" when git history is missing or shallow (a shallow
  // clone would give every page the same date, which search engines would learn to ignore).
  const lastmodCache = new Map();
  const git = (args) => { try { return execSync(`git ${args}`, { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); } catch { return ""; } };
  const shallow = git("rev-parse --is-shallow-repository") !== "false";
  eleventyConfig.addFilter("lastmod", function (inputPath) {
    if (shallow || !inputPath) return "";
    if (!lastmodCache.has(inputPath)) {
      const dirty = git(`status --porcelain -- "${inputPath}"`);
      lastmodCache.set(inputPath, dirty ? "" : git(`log -1 --format=%cI -- "${inputPath}"`));
    }
    return lastmodCache.get(inputPath);
  });
  eleventyConfig.addFilter("dateFilter", function(date) {
    const d = date instanceof Date ? date : new Date(date);
    return d.toISOString().split('T')[0];
  });

  eleventyConfig.addShortcode("email", function(address, displayText = null) {
    const [user, domain] = address.split('@');
    const display = displayText || 'Contact Us';
    
    return `<a href="#" class="email-link" data-user="${user}" data-domain="${domain}">${display}</a>`;
  });

  // Optional: Add as a paired shortcode if you want custom link text
  eleventyConfig.addPairedShortcode("emailLink", function(content, address) {
    const [user, domain] = address.split('@');
    return `<a href="#" class="email-link" data-user="${user}" data-domain="${domain}">${content}</a>`;
  });

  return {
    dir: {
      input: "src",
      output: "_site"
    }
  };


};

export const config = {
  htmlTemplateEngine: "njk",
  markdownTemplateEngine: "njk"
};