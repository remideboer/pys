const test = require('node:test');
const assert = require('node:assert/strict');

const {
  PysStepFilter,
  pysLocationFromFrame,
} = require('../debug-step-filter');

const PYS_A = 'C:\\workspace\\main.pys';
const PYS_B = 'C:\\workspace\\helpers.pys';

function frame(sourcePath, line, generatedPath, generatedLine) {
  const value = { id: 1, line, source: { path: sourcePath } };
  if (generatedPath && typeof generatedLine === 'number') {
    value.generatedSource = { path: generatedPath, line: generatedLine };
  }
  return value;
}

function userStep(filter, command = 'next', threadId = 7) {
  filter.recordTopFrame(frame(PYS_A, 10, 'C:\\tmp\\main.py', 20));
  return filter.observeRequest({
    type: 'request',
    command,
    arguments: { threadId },
  });
}

test('Given a generated stop on the same PYS line, it repeats the native step', async () => {
  const filter = new PysStepFilter({ enabled: true });
  assert.equal(userStep(filter), 'user-step');
  const repeated = [];

  const result = await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame(PYS_A, 10, 'C:\\tmp\\main.py', 21),
    async (command, args) => repeated.push({ command, args }),
  );

  assert.equal(result, 'repeat');
  assert.deepEqual(repeated, [{ command: 'next', args: { threadId: 7 } }]);
});

test('Given an unmapped generated helper stop, it repeats the native step', async () => {
  const filter = new PysStepFilter({ enabled: true });
  userStep(filter, 'stepIn');
  const repeated = [];

  const result = await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame('C:\\tmp\\generated.py', 42),
    async (command, args) => repeated.push({ command, args }),
  );

  assert.equal(result, 'repeat');
  assert.equal(repeated[0].command, 'stepIn');
});

test('Given a different PYS line, it exposes the stop to the user', async () => {
  const filter = new PysStepFilter({ enabled: true });
  userStep(filter);
  let repeats = 0;

  const result = await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame(PYS_A, 11),
    async () => {
      repeats += 1;
    },
  );

  assert.equal(result, 'stop');
  assert.equal(repeats, 0);
  assert.deepEqual(filter.currentLocation, {
    path: PYS_A.toLowerCase(),
    line: 11,
    generatedPath: null,
    generatedLine: null,
  });
});

test('re-executing the same mapped statement in a loop remains visible', async () => {
  const filter = new PysStepFilter({ enabled: true });
  userStep(filter);

  const result = await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame(PYS_A, 10, 'C:\\tmp\\main.py', 20),
    async () => assert.fail('a real repeated PYS statement must remain visible'),
  );

  assert.equal(result, 'stop');
});

test('Step Into stops in another mapped PYS module', async () => {
  const filter = new PysStepFilter({ enabled: true });
  userStep(filter, 'stepIn');

  const result = await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame(PYS_B, 3),
    async () => assert.fail('must not repeat'),
  );

  assert.equal(result, 'stop');
});

test('disabled filter leaves native stepping unchanged', async () => {
  const filter = new PysStepFilter({ enabled: false });
  assert.equal(userStep(filter), 'ignored');
  const result = await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame(PYS_A, 10),
    async () => assert.fail('must not repeat'),
  );
  assert.equal(result, 'ignored');
});

test('breakpoint exception and pause stops are never repeated', async () => {
  for (const reason of ['breakpoint', 'exception', 'pause', 'data breakpoint']) {
    const filter = new PysStepFilter({ enabled: true });
    userStep(filter);
    const result = await filter.handleStopped(
      { type: 'event', event: 'stopped', body: { reason, threadId: 7 } },
      async () => frame(PYS_A, 10),
      async () => assert.fail(`must not repeat ${reason}`),
    );
    assert.equal(result, 'ignored');
  }
});

test('next stepIn and stepOut preserve their command and arguments', async () => {
  for (const command of ['next', 'stepIn', 'stepOut']) {
    const filter = new PysStepFilter({ enabled: true });
    userStep(filter, command, 9);
    const repeated = [];
    await filter.handleStopped(
      { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 9 } },
      async () => frame(PYS_A, 10),
      async (name, args) => repeated.push({ name, args }),
    );
    assert.deepEqual(repeated, [{ name: command, args: { threadId: 9 } }]);
  }
});

test('controller-generated step is not mistaken for a new user operation', async () => {
  const filter = new PysStepFilter({ enabled: true });
  userStep(filter);
  await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame(PYS_A, 10),
    async (command, args) => {
      const kind = filter.observeRequest({
        type: 'request',
        command,
        arguments: args,
      });
      assert.equal(kind, 'internal-step');
    },
  );
  assert.equal(filter.operation.start.line, 10);
  assert.equal(filter.operation.skips, 1);
});

test('bounded fail-safe stops after the configured skip count', async () => {
  const filter = new PysStepFilter({ enabled: true, maxSkips: 1 });
  userStep(filter);
  await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame(PYS_A, 10),
    async (command, args) => {
      filter.observeRequest({ type: 'request', command, arguments: args });
    },
  );

  const result = await filter.handleStopped(
    { type: 'event', event: 'stopped', body: { reason: 'step', threadId: 7 } },
    async () => frame(PYS_A, 10),
    async () => assert.fail('limit must not repeat'),
  );

  assert.equal(result, 'limit');
  assert.equal(filter.operation, null);
});

test('pysLocationFromFrame accepts only mapped PYS source frames', () => {
  assert.deepEqual(pysLocationFromFrame(frame(PYS_A, 8)), {
    path: PYS_A.toLowerCase(),
    line: 8,
    generatedPath: null,
    generatedLine: null,
  });
  assert.equal(pysLocationFromFrame(frame('C:\\tmp\\main.py', 8)), null);
  assert.equal(pysLocationFromFrame({ id: 1, line: 8 }), null);
});
