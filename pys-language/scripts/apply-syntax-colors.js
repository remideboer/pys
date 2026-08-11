/**
 * Apply pys-language/syntax-color-schemes.md → package.json tokenColorCustomizations.
 *
 * Scheme lines (usage first):
 *   Classes, types → types #8BE9FD
 * under ## theme: dark | light | high-contrast
 *
 * The middle field is a stable *role* id (not a color name). Hex is free-form.
 */
const fs = require("fs");
const path = require("path");

const extensionRoot = path.join(__dirname, "..");
const schemesPath = path.join(extensionRoot, "syntax-color-schemes.md");
const packagePath = path.join(extensionRoot, "package.json");

/** role → TextMate scopes (color names like Yellow are never keys). */
const ROLE_SCOPES = {
  comments: {
    scope: ["comment.line.number-sign.pys", "comment.block.pys"],
  },
  strings: {
    scope: ["string.quoted.double.pys", "string.quoted.single.pys"],
  },
  numbers: {
    scope: [
      "constant.numeric.integer.pys",
      "constant.numeric.float.pys",
      "constant.numeric.hex.pys",
      "constant.numeric.binary.pys",
      "constant.language.pys",
      "constant.character.escape.pys",
    ],
  },
  functions: {
    scope: ["entity.name.function.pys", "support.function.pys"],
  },
  types: {
    scope: [
      "storage.type.primitive.pys",
      "entity.name.type.pys",
      "entity.name.type.class.pys",
      "entity.name.type.interface.pys",
      "entity.name.type.struct.pys",
      "entity.name.type.data.pys",
      "entity.name.type.entity.pys",
      "entity.name.type.enum.pys",
    ],
  },
  "language-constants": {
    scope: ["variable.language.pys", "variable.other.constant.pys"],
  },
  keywords: {
    scope: [
      "keyword.control.pys",
      "keyword.operator.pys",
      "storage.modifier.pys",
      "punctuation.definition.decorator.pys",
      "entity.name.function.decorator.pys",
      "meta.function.decorator.pys",
    ],
  },
};

const REQUIRED_ROLES = Object.keys(ROLE_SCOPES);

const THEME_KEYS = {
  dark: "[*Dark*]",
  light: "[*Light*]",
  "high-contrast": "[*HighContrast*]",
};

/** role → package.json setting id (Settings UI color pickers). */
const ROLE_PACKAGE_SETTINGS = {
  comments: "pys.syntaxColors.comments",
  numbers: "pys.syntaxColors.numbers",
  strings: "pys.syntaxColors.strings",
  functions: "pys.syntaxColors.functions",
  types: "pys.syntaxColors.types",
  "language-constants": "pys.syntaxColors.languageConstants",
  keywords: "pys.syntaxColors.keywords",
};

const ROLE_SETTING_META = {
  comments: {
    order: 20,
    markdownDescription:
      "Color for comments (hex). Settings UI is text-only — open **[PYS: Customize Syntax Colors](command:pys.customizeSyntaxColors)** for a color square, picker, and **Use color** (live update). **Reset Setting** restores per-theme defaults.",
  },
  numbers: {
    order: 21,
    markdownDescription:
      "Color for numbers, booleans, and escapes (hex). Use **[PYS: Customize Syntax Colors](command:pys.customizeSyntaxColors)** for swatch + picker. **Reset Setting** restores defaults.",
  },
  strings: {
    order: 22,
    markdownDescription:
      "Color for string literals (hex). Use **[PYS: Customize Syntax Colors](command:pys.customizeSyntaxColors)** for swatch + picker. **Reset Setting** restores defaults.",
  },
  functions: {
    order: 23,
    markdownDescription:
      "Color for functions and methods (hex). Use **[PYS: Customize Syntax Colors](command:pys.customizeSyntaxColors)** for swatch + picker. **Reset Setting** restores defaults.",
  },
  types: {
    order: 24,
    markdownDescription:
      "Color for types (classes, primitives, structs, …) (hex). Use **[PYS: Customize Syntax Colors](command:pys.customizeSyntaxColors)** for swatch + picker. **Reset Setting** restores defaults.",
  },
  "language-constants": {
    order: 25,
    markdownDescription:
      "Color for `this` / `super` and named constants (hex). Use **[PYS: Customize Syntax Colors](command:pys.customizeSyntaxColors)** for swatch + picker. **Reset Setting** restores defaults.",
  },
  keywords: {
    order: 26,
    markdownDescription:
      "Color for keywords, storage modifiers, and decorators (hex). Use **[PYS: Customize Syntax Colors](command:pys.customizeSyntaxColors)** for swatch + picker. **Reset Setting** restores defaults.",
  },
};

/**
 * Sync Settings UI color defaults from the dark theme palette (picker preview).
 * Explicit user values still override; Reset clears the override.
 * @param {object} pkg
 * @param {{ role: string, hex: string, usage: string }[]} darkEntries
 */
function syncSyntaxColorSettings(pkg, darkEntries) {
  if (!pkg.contributes) {
    pkg.contributes = {};
  }
  if (!pkg.contributes.configuration) {
    pkg.contributes.configuration = { title: "PYS", properties: {} };
  }
  const props = pkg.contributes.configuration.properties || {};
  pkg.contributes.configuration.properties = props;

  const byRole = new Map(
    darkEntries.filter((e) => ROLE_SCOPES[e.role]).map((e) => [e.role, e]),
  );
  for (const role of REQUIRED_ROLES) {
    const entry = byRole.get(role);
    if (!entry) {
      throw new Error(`Dark theme missing role '${role}' for Settings color defaults`);
    }
    const key = ROLE_PACKAGE_SETTINGS[role];
    const meta = ROLE_SETTING_META[role];
    props[key] = {
      type: "string",
      format: "color",
      default: entry.hex,
      order: meta.order,
      markdownDescription: meta.markdownDescription,
    };
  }
}

/**
 * @param {string} markdown
 * @returns {Record<string, { usage: string, role: string, hex: string }[]>}
 */
function parseSchemes(markdown) {
  const themes = {};
  let current = null;
  const heading = /^##\s+theme:\s*(\S+)\s*$/i;
  // usage → role #hex   (role is kebab-case / letters, not a color name)
  const line =
    /^(.+?)\s*→\s*([a-z][a-z0-9-]*)\s+(#[0-9A-Fa-f]{6})\s*$/;

  for (const raw of markdown.split(/\r?\n/)) {
    const text = raw.trim();
    if (!text) {
      continue;
    }
    const h = heading.exec(text);
    if (h) {
      current = h[1].toLowerCase();
      themes[current] = [];
      continue;
    }
    if (!current || text.startsWith("#") || text === "---" || text.startsWith("```")) {
      continue;
    }
    const m = line.exec(text);
    if (!m) {
      continue;
    }
    themes[current].push({
      usage: m[1].trim(),
      role: m[2].trim(),
      hex: m[3].toUpperCase(),
    });
  }
  return themes;
}

/**
 * @param {{ usage: string, role: string, hex: string }[]} entries
 * @param {{ boldKeywords?: boolean }} [opts]
 */
function rulesFromEntries(entries, opts = {}) {
  const rules = [];
  const seen = new Set();
  for (const entry of entries) {
    const def = ROLE_SCOPES[entry.role];
    if (!def) {
      // background / selection / errors / … — keep in the md, ignore for TextMate
      continue;
    }
    if (seen.has(entry.role)) {
      throw new Error(`Duplicate role '${entry.role}' in scheme`);
    }
    seen.add(entry.role);
    const settings = { foreground: entry.hex };
    if (opts.boldKeywords && entry.role === "keywords") {
      settings.fontStyle = "bold";
    }
    rules.push({
      scope: [...def.scope],
      settings,
    });
  }
  const missing = REQUIRED_ROLES.filter((r) => !seen.has(r));
  if (missing.length) {
    throw new Error(
      `Scheme missing roles: ${missing.join(", ")} ` +
        `(need lines like: Strings, text content → strings #F1FA8C)`,
    );
  }
  return rules;
}

function apply() {
  const markdown = fs.readFileSync(schemesPath, "utf8");
  const themes = parseSchemes(markdown);
  const pkg = JSON.parse(fs.readFileSync(packagePath, "utf8"));

  const customizations = {};
  for (const [themeId, pkgKey] of Object.entries(THEME_KEYS)) {
    const entries = themes[themeId];
    if (!entries || !entries.length) {
      throw new Error(`Missing ## theme: ${themeId} section in syntax-color-schemes.md`);
    }
    customizations[pkgKey] = {
      textMateRules: rulesFromEntries(entries, {
        boldKeywords: themeId === "high-contrast",
      }),
    };
  }

  if (!pkg.contributes) {
    pkg.contributes = {};
  }
  pkg.contributes.configurationDefaults = {
    ...(pkg.contributes.configurationDefaults || {}),
    "editor.tokenColorCustomizations": customizations,
  };

  const darkEntries = themes.dark || [];
  syncSyntaxColorSettings(pkg, darkEntries);

  fs.writeFileSync(packagePath, `${JSON.stringify(pkg, null, 2)}\n`, "utf8");
  console.log(
    "Applied syntax-color-schemes.md → package.json tokenColorCustomizations + syntaxColors pickers",
  );
}

if (require.main === module) {
  try {
    apply();
  } catch (err) {
    console.error(err.message || err);
    process.exit(1);
  }
}

module.exports = {
  ROLE_SCOPES,
  REQUIRED_ROLES,
  ROLE_PACKAGE_SETTINGS,
  TOKEN_SCOPES: ROLE_SCOPES, // back-compat alias for tests
  THEME_KEYS,
  parseSchemes,
  rulesFromEntries,
  syncSyntaxColorSettings,
  apply,
};
