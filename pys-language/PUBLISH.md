# Publishing the PYS VS Code extension

Two student channels:

1. **GitHub Release** (zip + VSIX) — offline / LMS / ELO download
2. **Visual Studio Marketplace** — auto-update when `VSCE_PAT` is configured

Trunk-based: keep `main` releasable. Bump version and write notes on `main`,
then tag. No release branches.

## One-time setup (Marketplace, optional)

1. Create a Marketplace publisher whose id is **`remideboer`**
   (must match `publisher` in [`package.json`](package.json)):
   https://marketplace.visualstudio.com/manage  
   Sign in with the same Microsoft account you use for Azure DevOps.

2. Create an Azure DevOps **Personal Access Token**:
   https://dev.azure.com → User settings → Personal access tokens  
   - Organization: **All accessible organizations**  
   - Scopes: **Marketplace → Manage** (or Publish)

3. In the GitHub repo **Settings → Secrets and variables → Actions**, add:

   | Secret | Purpose |
   | --- | --- |
   | `VSCE_PAT` | Optional — VS Marketplace publish |
   | `OVSX_PAT` | Optional — [Open VSX](https://open-vsx.org/) (helps Cursor / VSCodium) |

Without these secrets, a tag still creates a **GitHub Release** with the student
zip and VSIX.

## Release a new version (DoD)

1. On `main`:
   - Bump `"version"` in [`package.json`](package.json) (and lockfile if needed).
   - Rewrite [`RELEASE_NOTES.md`](RELEASE_NOTES.md) for **that** version (must
     contain the version string — the publish workflow and `npm test` check
     that). Per-version **highlights** only; do not force old feature names into
     every notes rewrite (grammar / `extension.js` tests own lasting keywords).
   - Run local CI before push/tag:

```text
python tools/local_ci.py
```

2. Commit and push to `main`. Wait for the Extension CI workflow to pass.
3. Tag and push from the same tip of `main` (tag **must** match the version):

```bash
git tag extension-v0.0.79
git push origin extension-v0.0.79
```

4. Workflow [Publish extension](../.github/workflows/publish-extension.yml):
   - tests + packages VSIX + **`dist/pys-student-<version>.zip`**
   - creates a **GitHub Release** with curated notes (+ auto-generated commit
     list), VSIX, and ELO zip
   - publishes to Marketplace / Open VSX **only if** the matching secret is set

Upload the Release asset `pys-student-<version>.zip` to your ELO / LMS.

### Local builds

```powershell
cd pys-language
npm run package          # VSIX only
npm run package:elo      # VSIX + dist/pys-student-<version>.zip
```

Contributor shortcut (from repo root, after `pip install -e .`):

```powershell
.\install-extension.bat            # Windows
./install-extension.sh             # macOS/Linux
pys install extension              # same via CLI
pys install extension --no-build   # install newest existing VSIX only
```

Local Marketplace publish:

```powershell
$env:VSCE_PAT = "..."
cd pys-language
npm run publish:marketplace
```

## Student install

**Marketplace:** Extensions → **PYS Language Support**, or `ext install remideboer.pys-language`.

**GitHub Release / ELO zip:** unzip → run `install.cmd` (Windows) or `./install.sh` → reload VS Code.  
Needs Python 3.10+ on PATH. The zip includes the extension with bundled transpiler (no `pip install` of this repo).
