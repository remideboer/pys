# Publishing the PYS VS Code extension

Two student channels:

1. **Visual Studio Marketplace** (preferred — auto-update)
2. **ELO zip** — offline / LMS download + local `install.cmd`

## One-time setup (Marketplace)

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
   | `VSCE_PAT` | Required — VS Marketplace publish |
   | `OVSX_PAT` | Optional — [Open VSX](https://open-vsx.org/) (helps Cursor / VSCodium) |

## Release a new version

1. Bump `"version"` in [`package.json`](package.json) (e.g. `0.0.31`).
2. Commit and push to `main`.
3. Tag and push (tag **must** match the version):

```bash
git tag extension-v0.0.31
git push origin extension-v0.0.31
```

4. Workflow [Publish extension](../.github/workflows/publish-extension.yml):
   - tests + packages VSIX
   - publishes to Marketplace
   - builds **`dist/pys-student-<version>.zip`** (ELO pack)
   - attaches VSIX + ELO zip to a **GitHub Release**

Upload the Release asset `pys-student-<version>.zip` to your ELO.

### Local builds

```powershell
cd pys-language
npm run package          # VSIX only
npm run package:elo      # VSIX + dist/pys-student-<version>.zip
```

Local Marketplace publish:

```powershell
$env:VSCE_PAT = "..."
cd pys-language
npm run publish:marketplace
```

## Student install

**Marketplace:** Extensions → **PYS Language Support**, or `ext install remideboer.pys-language`.

**ELO zip:** unzip → run `install.cmd` (Windows) or `./install.sh` → reload VS Code.  
Needs Python 3.10+ on PATH. The zip includes the extension with bundled transpiler (no `pip install` of this repo).
