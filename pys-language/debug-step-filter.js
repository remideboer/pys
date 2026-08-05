'use strict';

const { normalizePathKey } = require('./debug-map');

const STEP_COMMANDS = new Set(['next', 'stepIn', 'stepOut']);
const CANCEL_COMMANDS = new Set([
  'continue',
  'reverseContinue',
  'pause',
  'restart',
  'terminate',
  'disconnect',
]);
const DEFAULT_MAX_SKIPS = 100;

function pysLocationFromFrame(frame) {
  const sourcePath = frame && frame.source && frame.source.path;
  const line = frame && frame.line;
  if (
    typeof sourcePath !== 'string' ||
    !sourcePath.toLowerCase().endsWith('.pys') ||
    typeof line !== 'number'
  ) {
    return null;
  }
  const generated = frame.generatedSource;
  const generatedPath =
    generated && typeof generated.path === 'string'
      ? normalizePathKey(generated.path)
      : null;
  const generatedLine =
    generated && typeof generated.line === 'number' ? generated.line : null;
  return {
    path: normalizePathKey(sourcePath),
    line,
    generatedPath,
    generatedLine,
  };
}

function sameLocation(left, right) {
  return Boolean(
    left &&
      right &&
      left.path === right.path &&
      left.line === right.line,
  );
}

function sameGeneratedLocation(left, right) {
  return Boolean(
    left &&
      right &&
      left.generatedPath &&
      right.generatedPath &&
      left.generatedPath === right.generatedPath &&
      left.generatedLine === right.generatedLine,
  );
}

class PysStepFilter {
  constructor({ enabled = true, maxSkips = DEFAULT_MAX_SKIPS } = {}) {
    this.enabled = Boolean(enabled);
    this.maxSkips = Math.max(1, Number(maxSkips) || DEFAULT_MAX_SKIPS);
    this.currentLocation = null;
    this.operation = null;
    this.internalStepRequests = 0;
    this.handlingStop = false;
  }

  setEnabled(enabled) {
    this.enabled = Boolean(enabled);
    this.cancelOperation();
  }

  recordTopFrame(frame) {
    this.currentLocation = pysLocationFromFrame(frame);
    return this.currentLocation;
  }

  observeRequest(message) {
    const command = message && message.command;
    if (CANCEL_COMMANDS.has(command)) {
      this.cancelOperation();
      return 'cancelled';
    }
    if (!STEP_COMMANDS.has(command)) {
      return 'ignored';
    }
    if (this.internalStepRequests > 0) {
      this.internalStepRequests -= 1;
      return 'internal-step';
    }
    if (!this.enabled) {
      return 'ignored';
    }
    this.operation = {
      command,
      args: { ...((message && message.arguments) || {}) },
      start: this.currentLocation,
      skips: 0,
    };
    return 'user-step';
  }

  cancelOperation() {
    this.operation = null;
    this.internalStepRequests = 0;
    this.handlingStop = false;
  }

  async handleStopped(message, fetchTopFrame, repeatStep) {
    const body = message && message.body;
    if (
      !this.enabled ||
      !this.operation ||
      !body ||
      body.reason !== 'step' ||
      this.handlingStop
    ) {
      if (body && body.reason && body.reason !== 'step') {
        this.cancelOperation();
      }
      return 'ignored';
    }

    this.handlingStop = true;
    try {
      const topFrame = await fetchTopFrame(body.threadId);
      const location = pysLocationFromFrame(topFrame);
      if (
        location &&
        (
          !sameLocation(location, this.operation.start) ||
          sameGeneratedLocation(location, this.operation.start)
        )
      ) {
        this.currentLocation = location;
        this.operation = null;
        return 'stop';
      }
      if (this.operation.skips >= this.maxSkips) {
        this.currentLocation = location;
        this.operation = null;
        return 'limit';
      }

      const command = this.operation.command;
      const args = { ...this.operation.args };
      this.operation.skips += 1;
      this.internalStepRequests += 1;
      try {
        await repeatStep(command, args);
      } catch (error) {
        this.internalStepRequests = Math.max(0, this.internalStepRequests - 1);
        this.operation = null;
        throw error;
      }
      return 'repeat';
    } finally {
      this.handlingStop = false;
    }
  }
}

module.exports = {
  DEFAULT_MAX_SKIPS,
  STEP_COMMANDS,
  PysStepFilter,
  pysLocationFromFrame,
  sameLocation,
  sameGeneratedLocation,
};
