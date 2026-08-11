/**
 * Webview: color swatch + hex + Use color → live PYS token colors.
 */
const vscode = require('vscode');
const {
  ROLE_SETTING_KEYS,
  ROLE_SCOPES,
  normalizeHex,
  mergeTokenColorCustomizations,
  overridesFromInspect,
} = require('./syntax-colors-ui.js');

const ROLE_LABELS = {
  comments: 'Comments',
  numbers: 'Numbers / booleans',
  strings: 'Strings',
  functions: 'Functions / methods',
  types: 'Types (classes, primitives, …)',
  'language-constants': 'this / super / constants',
  keywords: 'Keywords / modifiers',
};

/**
 * @param {typeof import('vscode')} vscodeApi
 * @param {() => Promise<void>} syncAll
 */
function registerSyntaxColorPicker(vscodeApi, syncAll) {
  const ConfigurationTarget = vscodeApi.ConfigurationTarget;

  async function currentRoleColors() {
    const pys = vscodeApi.workspace.getConfiguration('pys');
    const colors = {};
    for (const role of Object.keys(ROLE_SCOPES)) {
      const key = ROLE_SETTING_KEYS[role];
      const raw = pys.get(key);
      try {
        colors[role] = normalizeHex(String(raw || '#888888'));
      } catch {
        colors[role] = '#888888';
      }
    }
    return colors;
  }

  /**
   * Live preview one role without persisting pys.syntaxColors until Use color.
   * @param {string} role
   * @param {string} hex
   */
  async function previewRole(role, hex) {
    if (!ROLE_SCOPES[role]) {
      return;
    }
    const pys = vscodeApi.workspace.getConfiguration('pys');
    const combined = {
      ...overridesFromInspect((key) => pys.inspect(key), 'global'),
      [role]: normalizeHex(hex),
    };
    const editor = vscodeApi.workspace.getConfiguration('editor');
    const insp = editor.inspect('tokenColorCustomizations');
    const merged = mergeTokenColorCustomizations(insp.globalValue, combined);
    await editor.update(
      'tokenColorCustomizations',
      merged,
      ConfigurationTarget.Global,
    );
  }

  /**
   * Persist one role into Settings (fills the color field) and sync.
   * @param {string} role
   * @param {string} hex
   */
  async function useColor(role, hex) {
    const key = ROLE_SETTING_KEYS[role];
    if (!key) {
      return;
    }
    const value = normalizeHex(hex);
    const pys = vscodeApi.workspace.getConfiguration('pys');
    await pys.update(key, value, ConfigurationTarget.Global);
    await syncAll();
  }

  function panelHtml(colors) {
    const rows = Object.keys(ROLE_SCOPES)
      .map((role) => {
        const hex = colors[role] || '#888888';
        const label = ROLE_LABELS[role] || role;
        return `<div class="row" data-role="${role}">
  <div class="label">${label}</div>
  <input class="swatch" type="color" value="${hex.toLowerCase()}" aria-label="${label} color" />
  <input class="hex" type="text" spellcheck="false" value="${hex}" maxlength="7" aria-label="${label} hex" />
  <button class="use" type="button">Use color</button>
</div>`;
      })
      .join('\n');

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';" />
  <style>
    body {
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      color: var(--vscode-foreground);
      padding: 12px 16px 24px;
    }
    h1 { font-size: 1.1rem; font-weight: 600; margin: 0 0 8px; }
    p.hint { opacity: 0.85; margin: 0 0 16px; max-width: 40rem; }
    .row {
      display: grid;
      grid-template-columns: minmax(10rem, 1.4fr) 2.2rem minmax(5.5rem, 6.5rem) auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 10px;
    }
    .label { line-height: 1.3; }
    .swatch {
      width: 2rem;
      height: 2rem;
      padding: 0;
      border: 1px solid var(--vscode-input-border, #666);
      border-radius: 3px;
      cursor: pointer;
      background: transparent;
    }
    .hex {
      font-family: var(--vscode-editor-font-family, monospace);
      background: var(--vscode-input-background);
      color: var(--vscode-input-foreground);
      border: 1px solid var(--vscode-input-border, #666);
      border-radius: 2px;
      padding: 4px 8px;
    }
    .use {
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: none;
      border-radius: 2px;
      padding: 5px 12px;
      cursor: pointer;
    }
    .use:hover { background: var(--vscode-button-hoverBackground); }
    .status { margin-top: 14px; opacity: 0.9; min-height: 1.2em; }
  </style>
</head>
<body>
  <h1>PYS syntax colors</h1>
  <p class="hint">
    Click the color square to open the picker. Hex updates as you adjust.
    Click <strong>Use color</strong> to save that role into Settings and update the editor.
  </p>
  ${rows}
  <div class="status" id="status"></div>
  <script>
    const vscode = acquireVsCodeApi();
    const status = document.getElementById('status');

    function normalizeHex(raw) {
      const s = String(raw || '').trim();
      if (/^#[0-9A-Fa-f]{6}$/.test(s)) return s.toUpperCase();
      if (/^#[0-9A-Fa-f]{3}$/.test(s)) {
        return ('#' + s[1]+s[1]+s[2]+s[2]+s[3]+s[3]).toUpperCase();
      }
      return null;
    }

    function setStatus(msg) {
      status.textContent = msg || '';
    }

    for (const row of document.querySelectorAll('.row')) {
      const swatch = row.querySelector('.swatch');
      const hex = row.querySelector('.hex');
      const use = row.querySelector('.use');
      const role = row.getAttribute('data-role');

      swatch.addEventListener('input', () => {
        hex.value = swatch.value.toUpperCase();
        vscode.postMessage({ type: 'preview', role, hex: hex.value });
        setStatus('Previewing… click Use color to save ' + role);
      });

      hex.addEventListener('input', () => {
        const n = normalizeHex(hex.value);
        if (!n) return;
        hex.value = n;
        swatch.value = n.toLowerCase();
        vscode.postMessage({ type: 'preview', role, hex: n });
        setStatus('Previewing… click Use color to save ' + role);
      });

      use.addEventListener('click', () => {
        const n = normalizeHex(hex.value) || normalizeHex(swatch.value);
        if (!n) {
          setStatus('Invalid hex for ' + role);
          return;
        }
        hex.value = n;
        swatch.value = n.toLowerCase();
        vscode.postMessage({ type: 'use', role, hex: n });
        setStatus('Applied ' + role + ' → ' + n);
      });
    }
  </script>
</body>
</html>`;
  }

  const sub = vscodeApi.commands.registerCommand('pys.customizeSyntaxColors', async () => {
    const colors = await currentRoleColors();
    const panel = vscodeApi.window.createWebviewPanel(
      'pysSyntaxColors',
      'PYS Syntax Colors',
      vscodeApi.ViewColumn.Beside,
      { enableScripts: true, retainContextWhenHidden: true },
    );
    panel.webview.html = panelHtml(colors);

    const disposable = panel.webview.onDidReceiveMessage(async (msg) => {
      try {
        if (msg && msg.type === 'preview' && msg.role && msg.hex) {
          await previewRole(msg.role, msg.hex);
          return;
        }
        if (msg && msg.type === 'use' && msg.role && msg.hex) {
          await useColor(msg.role, msg.hex);
        }
      } catch (err) {
        void vscodeApi.window.showErrorMessage(
          `PYS color picker: ${err && err.message ? err.message : err}`,
        );
      }
    });

    panel.onDidDispose(() => {
      disposable.dispose();
      void syncAll();
    });
  });

  return sub;
}

module.exports = {
  registerSyntaxColorPicker,
  ROLE_LABELS,
};
