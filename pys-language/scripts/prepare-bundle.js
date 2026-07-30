/**
 * Copy ../transpiler into bundled/transpiler for the VSIX / Extension Host.
 * Also copy ../LICENSE so vsce can publish.
 * Run from pys-language via: npm run prepare-bundle
 */
const fs = require("fs");
const path = require("path");

const extensionRoot = path.join(__dirname, "..");
const repoRoot = path.join(extensionRoot, "..");
const src = path.join(repoRoot, "transpiler");
const destRoot = path.join(extensionRoot, "bundled");
const dest = path.join(destRoot, "transpiler");
const licenseSrc = path.join(repoRoot, "LICENSE");
const licenseDest = path.join(extensionRoot, "LICENSE");

function copyDir(from, to) {
  fs.mkdirSync(to, { recursive: true });
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    if (entry.name === "__pycache__" || entry.name.endsWith(".pyc")) {
      continue;
    }
    const sourcePath = path.join(from, entry.name);
    const destPath = path.join(to, entry.name);
    if (entry.isDirectory()) {
      copyDir(sourcePath, destPath);
    } else {
      fs.copyFileSync(sourcePath, destPath);
    }
  }
}

if (!fs.existsSync(src)) {
  console.error("transpiler package not found at:", src);
  process.exit(1);
}

fs.rmSync(destRoot, { recursive: true, force: true });
copyDir(src, dest);
console.log("Bundled transpiler ->", dest);

if (fs.existsSync(licenseSrc)) {
  fs.copyFileSync(licenseSrc, licenseDest);
  console.log("Copied LICENSE ->", licenseDest);
} else {
  console.warn("LICENSE not found at repo root; Marketplace publish may warn.");
}
