/**
 * Host runtime probe + install plans (Python / Node).
 * Kept free of vscode so unit tests can run under node --test.
 */

'use strict';

const { spawnSync } = require('child_process');

/** @typedef {'python' | 'javascript'} EmitTarget */
/** @typedef {'python' | 'node'} RuntimeKind */

const STABLE_PYTHON_VERSIONS = [
  {
    id: '3.13',
    label: 'Python 3.13',
    description: 'Latest stable',
    wingetId: 'Python.Python.3.13',
    brewFormula: 'python@3.13',
    aptPackage: 'python3',
    docsUrl: 'https://www.python.org/downloads/',
  },
  {
    id: '3.12',
    label: 'Python 3.12',
    description: 'Current stable',
    wingetId: 'Python.Python.3.12',
    brewFormula: 'python@3.12',
    aptPackage: 'python3',
    docsUrl: 'https://www.python.org/downloads/',
  },
  {
    id: '3.11',
    label: 'Python 3.11',
    description: 'Long-term support class',
    wingetId: 'Python.Python.3.11',
    brewFormula: 'python@3.11',
    aptPackage: 'python3',
    docsUrl: 'https://www.python.org/downloads/',
  },
];

const STABLE_NODE_VERSIONS = [
  {
    id: '22',
    label: 'Node.js 22 LTS',
    description: 'Active LTS',
    wingetId: 'OpenJS.NodeJS.LTS',
    brewFormula: 'node@22',
    aptPackage: 'nodejs',
    docsUrl: 'https://nodejs.org/en/download',
  },
  {
    id: '20',
    label: 'Node.js 20 LTS',
    description: 'Maintenance LTS',
    wingetId: 'OpenJS.NodeJS.LTS',
    brewFormula: 'node@20',
    aptPackage: 'nodejs',
    docsUrl: 'https://nodejs.org/en/download',
  },
];

/**
 * @param {EmitTarget | string} target
 * @returns {{ python: boolean, node: boolean }}
 */
function resolveToolchainNeeds(target) {
  const normalized = String(target || 'python').trim().toLowerCase();
  return {
    python: true,
    node: normalized === 'javascript',
  };
}

/**
 * @param {string[]} names
 * @param {{ spawnSync?: typeof spawnSync, platform?: NodeJS.Platform }} [opts]
 * @returns {string | null} first command that exits 0
 */
function probeCommand(names, opts = {}) {
  const run = opts.spawnSync || spawnSync;
  const platform = opts.platform || process.platform;
  const list = Array.isArray(names) ? names : [];
  for (const name of list) {
    if (!name || typeof name !== 'string') {
      continue;
    }
    if (platform === 'win32') {
      const where = run('where', [name], {
        encoding: 'utf8',
        windowsHide: true,
        shell: false,
      });
      if (where && where.status === 0 && String(where.stdout || '').trim()) {
        return name;
      }
      continue;
    }
    const which = run('which', [name], {
      encoding: 'utf8',
      windowsHide: true,
      shell: false,
    });
    if (which && which.status === 0 && String(which.stdout || '').trim()) {
      return name;
    }
  }
  return null;
}

/**
 * @param {{ spawnSync?: typeof spawnSync, platform?: NodeJS.Platform }} [opts]
 * @returns {string | null}
 */
function probePython(opts = {}) {
  const platform = opts.platform || process.platform;
  if (platform === 'win32') {
    return probeCommand(['python', 'python3', 'py'], opts);
  }
  return probeCommand(['python3', 'python'], opts);
}

/**
 * @param {{ spawnSync?: typeof spawnSync, platform?: NodeJS.Platform }} [opts]
 * @returns {string | null}
 */
function probeNode(opts = {}) {
  return probeCommand(['node'], opts);
}

/**
 * @param {RuntimeKind} kind
 * @returns {typeof STABLE_PYTHON_VERSIONS}
 */
function stableVersionsFor(kind) {
  return kind === 'node' ? STABLE_NODE_VERSIONS : STABLE_PYTHON_VERSIONS;
}

/**
 * @param {RuntimeKind} kind
 * @param {string} versionId
 * @param {NodeJS.Platform} [platform]
 * @param {{ brewAvailable?: boolean }} [hints]
 * @returns {{
 *   mode: 'winget' | 'brew' | 'docs',
 *   command: string | null,
 *   docsUrl: string,
 *   hint: string,
 * }}
 */
function installPlan(kind, versionId, platform = process.platform, hints = {}) {
  const versions = stableVersionsFor(kind);
  const entry = versions.find((v) => v.id === versionId) || versions[0];
  const docsUrl = entry.docsUrl;
  if (platform === 'win32') {
    return {
      mode: 'winget',
      command: `winget install -e --id ${entry.wingetId} --accept-package-agreements --accept-source-agreements`,
      docsUrl,
      hint: `Installs ${entry.label} via winget. Restart the IDE terminal after install so PATH updates.`,
    };
  }
  if (platform === 'darwin') {
    const brewOk =
      hints.brewAvailable === true
        ? true
        : hints.brewAvailable === false
          ? false
          : Boolean(probeCommand(['brew'], { platform: 'darwin' }));
    if (brewOk) {
      return {
        mode: 'brew',
        command: `brew install ${entry.brewFormula}`,
        docsUrl,
        hint: `Installs ${entry.label} via Homebrew. Open a new terminal after install.`,
      };
    }
  }
  if (platform === 'linux') {
    return {
      mode: 'docs',
      command: null,
      docsUrl,
      hint:
        `Install ${entry.label} with your distro package manager, e.g. ` +
        `\`sudo apt install ${entry.aptPackage}\` (Debian/Ubuntu) or see ${docsUrl}`,
    };
  }
  return {
    mode: 'docs',
    command: null,
    docsUrl,
    hint: `Install ${entry.label} from ${docsUrl}, then reload the IDE.`,
  };
}

/**
 * Build the shell line to send to a terminal for an install plan.
 * @param {{ mode: string, command: string | null, docsUrl: string, hint: string }} plan
 * @param {NodeJS.Platform} [platform]
 * @returns {string}
 */
function terminalInstallLine(plan, platform = process.platform) {
  if (plan.command) {
    return plan.command;
  }
  if (platform === 'win32') {
    return `start "" "${plan.docsUrl}"`;
  }
  if (platform === 'darwin') {
    return `open "${plan.docsUrl}"`;
  }
  return `xdg-open "${plan.docsUrl}" || echo "${plan.hint}"`;
}

module.exports = {
  STABLE_NODE_VERSIONS,
  STABLE_PYTHON_VERSIONS,
  installPlan,
  probeCommand,
  probeNode,
  probePython,
  resolveToolchainNeeds,
  stableVersionsFor,
  terminalInstallLine,
};
