const now = new Date();

// Import 11ty plugins
import eleventyNavigationPlugin from "@11ty/eleventy-navigation";

export default function (eleventyConfig) {
  eleventyConfig.setInputDirectory("src");
  eleventyConfig.setIncludesDirectory("_includes");
  eleventyConfig.setLayoutsDirectory("_layouts");

  eleventyConfig.addPassthroughCopy("src/assets/scans/");
  eleventyConfig.addPassthroughCopy("src/assets/images/");
  eleventyConfig.addPassthroughCopy("src/robots.txt");
  eleventyConfig.addPassthroughCopy("src/manifest.webmanifest");
  eleventyConfig.addPassthroughCopy("src/_headers");

  eleventyConfig.addWatchTarget("src");
  eleventyConfig.setServerOptions({
    liveReload: true
  });

  // read data from .env file to determine dev or prod
  eleventyConfig.addGlobalData("env", process.env.ELEVENTY_ENV);

  // 11ty Plugins
  eleventyConfig.addPlugin(eleventyNavigationPlugin);

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