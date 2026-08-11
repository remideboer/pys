/**
 * User-facing PYS syntax color overrides (Settings color pickers).
 *
 * Pure merge helpers are vscode-free for unit tests. The activate wiring
 * writes editor.tokenColorCustomizations only for roles the user has set
 * under pys.syntaxColors.* (inspect.globalValue / workspaceValue).
 */
const {
  ROLE_SCOPES,
  THEME_KEYS,
} = require('./scripts/apply-syntax-colors.js');

/** role id → setting key under `pys` configuration section */
const ROLE_SETTING_KEYS = {
  comments: 'syntaxColors.comments',
  numbers: 'syntaxColors.numbers',
  strings: 'syntaxColors.strings',
  functions: 'syntaxColors.functions',
  types: 'syntaxColors.types',
  'language-constants': 'syntaxColors.languageConstants',
  keywords: 'syntaxColors.keywords',
};

const THEME_PKG_KEYS = Object.values(THEME_KEYS);

/**
 * @param {unknown} scope
 * @param {string[]} expected
 */
function scopesEqual(scope, expected) {
  if (!Array.isArray(scope) || scope.length !== expected.length) {
    return false;
  }
  return scope.every((s, i) => s === expected[i]);
}

/**
 * @param {{ scope?: unknown }} rule
 */
function isManagedPysRule(rule) {
  if (!rule || !Array.isArray(rule.scope)) {
    return false;
  }
  return Object.values(ROLE_SCOPES).some((def) => scopesEqual(rule.scope, def.scope));
}

/**
 * @param {string} hex
 * @returns {string}
 */
function normalizeHex(hex) {
  const s = String(hex || '').trim();
  if (/^#[0-9A-Fa-f]{6}$/.test(s)) {
    return s.toUpperCase();
  }
  if (/^#[0-9A-Fa-f]{8}$/.test(s)) {
    return s.slice(0, 7).toUpperCase();
  }
  if (/^#[0-9A-Fa-f]{3}$/.test(s)) {
    const r = s[1];
    const g = s[2];
    const b = s[3];
    return `#${r}${r}${g}${g}${b}${b}`.toUpperCase();
  }
  throw new Error(`Invalid color: ${hex}`);
}

/**
 * @param {Record<string, string>} roleToHex
 * @param {{ highContrastBoldKeywords?: boolean }} [opts]
 * @returns {{ scope: string[], settings: { foreground: string, fontStyle?: string } }[]}
 */
function rulesForOverrides(roleToHex, opts = {}) {
  const rules = [];
  for (const role of Object.keys(ROLE_SCOPES)) {
    const hex = roleToHex[role];
    if (!hex) {
      continue;
    }
    const settings = { foreground: normalizeHex(hex) };
    if (opts.highContrastBoldKeywords && role === 'keywords') {
      settings.fontStyle = 'bold';
    }
    rules.push({
      scope: [...ROLE_SCOPES[role].scope],
      settings,
    });
  }
  return rules;
}

/**
 * Strip PYS-managed TextMate rules, then attach current overrides per theme.
 * Preserves unrelated tokenColorCustomizations (other languages, user rules).
 *
 * @param {unknown} existing
 * @param {Record<string, string>} roleToHex  role → #RRGGBB (only explicit overrides)
 * @returns {object|undefined} undefined when nothing remains to store
 */
function mergeTokenColorCustomizations(existing, roleToHex) {
  const next =
    existing && typeof existing === 'object' && !Array.isArray(existing)
      ? JSON.parse(JSON.stringify(existing))
      : {};

  const applyToThemeBlock = (block, boldKeywords) => {
    const kept = Array.isArray(block.textMateRules)
      ? block.textMateRules.filter((r) => !isManagedPysRule(r))
      : [];
    const added = rulesForOverrides(roleToHex, {
      highContrastBoldKeywords: boldKeywords,
    });
    const rules = kept.concat(added);
    if (rules.length) {
      block.textMateRules = rules;
    } else {
      delete block.textMateRules;
    }
  };

  // Top-level textMateRules (all themes)
  if (Array.isArray(next.textMateRules) || Object.keys(roleToHex).length) {
    const kept = Array.isArray(next.textMateRules)
      ? next.textMateRules.filter((r) => !isManagedPysRule(r))
      : [];
    // Do not put role overrides at top-level — keep them theme-scoped so HC bold works.
    if (kept.length) {
      next.textMateRules = kept;
    } else {
      delete next.textMateRules;
    }
  }

  for (const themeKey of THEME_PKG_KEYS) {
    const bold = themeKey === '[*HighContrast*]';
    if (!next[themeKey]) {
      if (!Object.keys(roleToHex).length) {
        continue;
      }
      next[themeKey] = {};
    }
    if (typeof next[themeKey] !== 'object' || Array.isArray(next[themeKey])) {
      next[themeKey] = {};
    }
    applyToThemeBlock(next[themeKey], bold);
    if (Object.keys(next[themeKey]).length === 0) {
      delete next[themeKey];
    }
  }

  return Object.keys(next).length ? next : undefined;
}

/**
 * @param {unknown} a
 * @param {unknown} b
 */
function jsonEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Read explicit overrides from a vscode Configuration inspect snapshot.
 * @param {(key: string) => { globalValue?: unknown, workspaceValue?: unknown }} inspectPys
 * @param {'global'|'workspace'} layer
 * @returns {Record<string, string>}
 */
function overridesFromInspect(inspectPys, layer) {
  const out = {};
  for (const [role, settingKey] of Object.entries(ROLE_SETTING_KEYS)) {
    const insp = inspectPys(settingKey);
    const raw = layer === 'global' ? insp.globalValue : insp.workspaceValue;
    if (raw === undefined || raw === null || raw === '') {
      continue;
    }
    try {
      out[role] = normalizeHex(String(raw));
    } catch {
      // ignore invalid colors
    }
  }
  return out;
}

/**
 * Wire Settings color pickers → editor.tokenColorCustomizations.
 * Returns a composite disposable (config listener + picker command).
 * @param {typeof import('vscode')} vscode
 */
function registerSyntaxColorSettings(vscode) {
  const ConfigurationTarget = vscode.ConfigurationTarget;

  async function syncLayer(layer) {
    const target =
      layer === 'global' ? ConfigurationTarget.Global : ConfigurationTarget.Workspace;
    const pys = vscode.workspace.getConfiguration('pys');
    const overrides = overridesFromInspect((key) => pys.inspect(key), layer);

    const editor = vscode.workspace.getConfiguration('editor');
    const insp = editor.inspect('tokenColorCustomizations');
    const previous = layer === 'global' ? insp.globalValue : insp.workspaceValue;
    const merged = mergeTokenColorCustomizations(previous, overrides);

    if (jsonEqual(previous === undefined ? undefined : previous, merged)) {
      return;
    }
    await editor.update('tokenColorCustomizations', merged, target);
  }

  async function syncAll() {
    await syncLayer('global');
    await syncLayer('workspace');
  }

  void syncAll();

  const configSub = vscode.workspace.onDidChangeConfiguration((e) => {
    if (e.affectsConfiguration('pys.syntaxColors')) {
      void syncAll();
    }
  });

  const { registerSyntaxColorPicker } = require('./syntax-color-picker.js');
  const pickerSub = registerSyntaxColorPicker(vscode, syncAll);

  return {
    dispose() {
      configSub.dispose();
      pickerSub.dispose();
    },
  };
}

module.exports = {
  ROLE_SETTING_KEYS,
  ROLE_SCOPES,
  THEME_PKG_KEYS,
  scopesEqual,
  isManagedPysRule,
  normalizeHex,
  rulesForOverrides,
  mergeTokenColorCustomizations,
  overridesFromInspect,
  registerSyntaxColorSettings,
};
