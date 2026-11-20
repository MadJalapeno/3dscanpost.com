const childProcess = require("child_process");

// Run a git command; return "" if git or the repo isn't available.
const git = (args) => {
  try {
    return childProcess.execSync(`git ${args}`, { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch (e) {
    return "";
  }
};

module.exports = () => ({
  hash: process.env.GIT_COMMIT_HASH || git("rev-parse --short HEAD"),
  commitDate: git("log -1 --format=%cI"), // when the deployed commit was made
  date: new Date().toISOString(),         // when this build ran
});
