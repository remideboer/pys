'use strict';

const fs = require('fs');
const path = require('path');

function normalizedRelativeMain(projectRoot, filePath) {
  const root = path.resolve(projectRoot);
  const file = path.resolve(filePath);
  const relative = path.relative(root, file);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error('Entrypoint must be a .pys file inside the project.');
  }
  if (path.extname(relative).toLowerCase() !== '.pys') {
    throw new Error('Entrypoint must be a .pys file.');
  }
  return relative.replace(/\\/g, '/');
}

function readProjectMain(text) {
  let inProject = false;
  for (const line of String(text || '').split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }
    if (/^\[[^\]]+\]$/.test(trimmed)) {
      inProject = trimmed.toLowerCase() === '[project]';
      continue;
    }
    if (!inProject) {
      continue;
    }
    const match = /^main\s*=\s*(['"])(.*?)\1\s*(?:#.*)?$/.exec(trimmed);
    if (match) {
      return match[2].trim();
    }
  }
  return '';
}

function setProjectMain(text, relativeMain) {
  const value = String(relativeMain || '').replace(/\\/g, '/');
  if (!value || value.startsWith('/') || value.split('/').includes('..')) {
    throw new Error('Project main must be a contained relative path.');
  }
  const newline = String(text || '').includes('\r\n') ? '\r\n' : '\n';
  const hadFinalNewline = !text || String(text).endsWith('\n');
  const lines = String(text || '').split(/\r?\n/);
  if (hadFinalNewline && lines[lines.length - 1] === '') {
    lines.pop();
  }
  let projectStart = -1;
  let projectEnd = lines.length;
  for (let index = 0; index < lines.length; index += 1) {
    const trimmed = lines[index].trim();
    if (!/^\[[^\]]+\]$/.test(trimmed)) {
      continue;
    }
    if (projectStart >= 0) {
      projectEnd = index;
      break;
    }
    if (trimmed.toLowerCase() === '[project]') {
      projectStart = index;
    }
  }
  const assignment = `main = ${JSON.stringify(value)}`;
  if (projectStart < 0) {
    if (lines.length && lines[lines.length - 1].trim()) {
      lines.push('');
    }
    lines.push('[project]', assignment);
  } else {
    let replaced = false;
    for (let index = projectStart + 1; index < projectEnd; index += 1) {
      if (/^\s*main\s*=/.test(lines[index])) {
        lines[index] = assignment;
        replaced = true;
        break;
      }
    }
    if (!replaced) {
      lines.splice(projectEnd, 0, assignment);
    }
  }
  return lines.join(newline) + (hadFinalNewline ? newline : '');
}

function findProjectManifest(startPath, workspaceRoot) {
  const root = path.resolve(workspaceRoot);
  let current = path.resolve(startPath || root);
  try {
    if (fs.statSync(current).isFile()) {
      current = path.dirname(current);
    }
  } catch (_error) {
    current = path.dirname(current);
  }
  while (current === root || current.startsWith(`${root}${path.sep}`)) {
    const candidate = path.join(current, 'pys.toml');
    if (fs.existsSync(candidate)) {
      return candidate;
    }
    if (current === root) {
      break;
    }
    current = path.dirname(current);
  }
  return null;
}

function resolveManifestMain(manifestPath) {
  if (!manifestPath || !fs.existsSync(manifestPath)) {
    return null;
  }
  const relative = readProjectMain(fs.readFileSync(manifestPath, 'utf8'));
  if (!relative) {
    return null;
  }
  const root = path.dirname(path.resolve(manifestPath));
  const candidate = path.resolve(root, relative);
  const contained = candidate === root || candidate.startsWith(`${root}${path.sep}`);
  return contained ? candidate : null;
}

module.exports = {
  findProjectManifest,
  normalizedRelativeMain,
  readProjectMain,
  resolveManifestMain,
  setProjectMain,
};
