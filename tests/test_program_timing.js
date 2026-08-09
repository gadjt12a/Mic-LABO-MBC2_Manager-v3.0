/*
 * Break-in program step timing — regression test.
 *
 *   node tests/test_program_timing.js
 *
 * The question this answers: does the program runner still end its steps on
 * time when setTimeout is throttled? Browsers throttle timers in a hidden or
 * occluded window, and that timer is what stops a step, so a throttled wake-up
 * runs the motor longer than the program asked for. See the comment above
 * appRunSchedule() in app/mbc2-dashboard.html.
 *
 * How it works: the real appRun functions are lifted out of the dashboard by
 * name and evaluated against stubs, so this exercises the shipped code rather
 * than a copy that can drift from it. A fake clock lets a 30-second step be
 * tested instantly, and the fake setTimeout can be told to fire late or never —
 * which is what a backgrounded browser actually does.
 *
 * If this file stops finding a function, the runner has been renamed or
 * restructured; fix NAMES rather than deleting the test.
 */
const fs = require('fs');
const path = require('path');

const HTML = process.argv[2] ||
             path.join(__dirname, '..', 'app', 'mbc2-dashboard.html');

// The frontend is deliberately a single file, so pull the script blocks out of
// the page rather than importing a module that does not exist.
const src = fs.readFileSync(HTML, 'utf8')
              .replace(/\r\n/g, '\n')
              .match(/<script[^>]*>([\s\S]*?)<\/script>/g)
              .map(b => b.replace(/^<script[^>]*>/, '').replace(/<\/script>$/, ''))
              .join('\n');

// That file puts a function's closing brace at column 0, so that is the terminator.
function grab(name) {
  const m = src.match(new RegExp('\\n(?:async )?function ' + name + '\\s*\\([^)]*\\)\\s*\\{'));
  if (!m) throw new Error('could not find function ' + name + ' — has it been renamed?');
  const start = m.index + 1;
  const end = src.indexOf('\n}\n', start);
  if (end < 0) throw new Error('could not find the end of ' + name);
  return src.slice(start, end + 3);
}

const NAMES = ['programTimeToSeconds',
               'appStepRunSec', 'appStepCoolSec', 'appStepVolts', 'appStepDir',
               'appRunApplyStep', 'appRunEnterPhase', 'appRunSchedule',
               'appRunCheckDeadline', 'appRunAdvance', 'finishAppProgram',
               'pauseAppProgram', 'resumeAppProgram', 'nextAppStep'];

// ── Fake clock ────────────────────────────────────────────────────────────
let now = 1000000;
let timers = [];
let seq = 0;
// throttleMs: how late a timer fires. 0 = perfectly accurate (visible window).
// Infinity = timers never fire at all (worst case for a hidden window).
let throttleMs = 0;

const clock = {
  now: () => now,
  setTimeout(fn, ms) {
    // appRunApplyStep's inter-command gap() awaits a setTimeout. If that went
    // on the fake clock it would deadlock: advance() would be awaiting the very
    // callback that is waiting for advance() to fire its timer. Zero-delay
    // waits go to the real event loop instead; only step deadlines (>0) are
    // simulated.
    if (!(ms > 0)) { setImmediate(fn); return -1; }
    const id = ++seq;
    timers.push({ id, fn, at: now + ms });
    return id;
  },
  clearTimeout(id) { timers = timers.filter(t => t.id !== id); },
  setInterval() { return ++seq; },   // the 1s ticker is throttled too; ignore it
  clearInterval() {},
};

// Advance the fake clock, firing timers as a throttled browser would.
async function advance(ms, onTick) {
  const target = now + ms;
  while (now < target) {
    now = Math.min(now + 50, target);          // 50ms granularity
    if (onTick) await onTick(now);             // e.g. deliver a telemetry row
    if (throttleMs === Infinity) continue;
    const due = timers.filter(t => t.at <= now - throttleMs);
    for (const t of due) {
      timers = timers.filter(x => x.id !== t.id);
      await t.fn();
    }
    await Promise.resolve();
  }
}

// ── Stubs ─────────────────────────────────────────────────────────────────
let sent = [];
let toasts = [];

// A device that always answers, so the test measures timing and nothing else.
const sandboxSetup = `
  let appRun = null, appRunTicker = null, appRunAdvancing = false;
  let recording = true, serialConnected = true, manualRun = false;
  const APP_RUN_CMD_GAP_MS = 0;
  function showToast(m, bad) { __toast(m, bad); }
  function updateAppRunButtons() {}
  function updateAppRunStatus() {}
  function formatTime(s) { return s + 's'; }
  function startRecording() {}
  async function deviceStop() { __sent('DEVICE_STOP'); }
  async function sendCommand(c) { __sent(c); }
  async function sendCommandAck(c, match) {
    __sent(c);
    if (c === 'START') return 'STATUS:RUNNING';
    if (c.startsWith('SET_DIRECTION:')) return 'STATUS:OK:SET_DIRECTION:' + c.split(':')[1];
    if (c.startsWith('SET_VOLTAGE:'))   return 'STATUS:OK:SET_VOLTAGE:' + c.split(':')[1];
    return null;
  }
`;

function build() {
  const body = sandboxSetup + NAMES.map(grab).join('\n') + `
    __api = { get appRun() { return appRun; },
              set appRun(v) { appRun = v; },
              appRunSchedule, appRunCheckDeadline, appRunAdvance,
              appRunEnterPhase, pauseAppProgram, resumeAppProgram, nextAppStep,
              get advancing() { return appRunAdvancing; },
              set advancing(v) { appRunAdvancing = v; } };
  `;
  const f = new Function('Date', 'setTimeout', 'clearTimeout', 'setInterval',
                         'clearInterval', '__toast', '__sent', `
    let __api; ${body} return __api;
  `);
  return f({ now: clock.now }, clock.setTimeout, clock.clearTimeout,
           clock.setInterval, clock.clearInterval,
           (m, bad) => toasts.push({ m, bad }),
           (c) => sent.push({ cmd: c, at: now }));
}

// ── Test driver ───────────────────────────────────────────────────────────
function reset() { now = 1000000; timers = []; seq = 0; sent = []; toasts = []; }

function makeRun(api, steps, cycles) {
  api.appRun = {
    name: 'T', label: 'T', steps, cycles, cycle: 1, stepIndex: 0,
    phase: 'run', paused: false, endsAt: 0, remaining: 0, timer: null,
    motorOn: false, dir: null, appliedVolts: null, voltageWarning: null,
    maxOverrunMs: 0
  };
  api.advancing = false;
}

// A two-step program: 30s at 2.0V then 20s at 3.0V, so the step boundary lands
// at 30000ms and the run ends at 50000ms.
async function scenario(label, opts) {
  reset();
  throttleMs = opts.throttleMs;
  const api = build();
  makeRun(api, [{ volts: 2.0, dir: 'R', time: '0:30', cool: '0:00' },
                { volts: 3.0, dir: 'R', time: '0:20', cool: '0:00' }], 1);

  const startedAt = now;
  await api.appRunEnterPhase('run');

  // Telemetry arrives at ~10Hz over SSE regardless of timer throttling.
  const tick = opts.telemetry ? async () => { api.appRunCheckDeadline(); } : null;
  // Long enough for the 50s program plus however late throttling makes the
  // timers — a 60s-throttled run cannot finish inside a 70s window.
  await advance(opts.windowMs || 70000, tick);

  // SET_VOLTAGE:3.0 is only sent when step 2 is applied, so it dates the boundary.
  const step2 = sent.filter(s => s.cmd === 'SET_VOLTAGE:3.0').map(s => s.at - startedAt)[0];
  const end   = sent.filter(s => s.cmd === 'DEVICE_STOP').map(s => s.at - startedAt)[0];
  const overruns = toasts.filter(t => /overran/.test(t.m)).map(t => t.m);

  console.log(`\n${label}`);
  console.log(`  throttle=${opts.throttleMs === Infinity ? 'timers never fire' : opts.throttleMs + 'ms'}` +
              `  telemetry=${opts.telemetry ? 'yes' : 'no'}`);
  console.log(`  finished: ${api.appRun === null}`);
  console.log(`  step 2 began at: ${step2 !== undefined ? step2 + 'ms (expected 30000)' : 'never'}`);
  console.log(`  run ended at:    ${end !== undefined ? end + 'ms (expected 50000)' : 'never'}`);
  console.log(`  overrun toasts:  ${overruns.length ? overruns.join(' | ') : 'none'}`);
  return { finished: api.appRun === null, step2, end, overruns };
}

(async () => {
  let fail = 0;
  const bad  = (m) => { console.log('  FAIL ' + m); fail++; };
  const near = (v, want, tol) => v !== undefined && Math.abs(v - want) <= tol;

  // 1. Visible window, timers accurate. Baseline: exact and quiet.
  const a = await scenario('1. Visible window (timers accurate)',
                           { throttleMs: 0, telemetry: true });
  if (!near(a.step2, 30000, 100)) bad('step 2 did not start on time');
  if (!near(a.end, 50000, 100))   bad('run did not end on time');
  if (a.overruns.length)          bad('warned about an on-time run');

  // 2. The original bug: hidden window, timers dead, no telemetry safety net.
  //    Kept as a test so the failure it guards against stays visible.
  const b = await scenario('2. Hidden window, NO telemetry check (pre-fix behaviour)',
                           { throttleMs: Infinity, telemetry: false });
  if (b.finished) bad('expected the run to stall without the telemetry check');
  else console.log('  (correctly reproduces the original bug: the step never ends)');

  // 3. The fix: hidden window, timers dead, telemetry still flowing.
  const c = await scenario('3. Hidden window, telemetry check active (the fix)',
                           { throttleMs: Infinity, telemetry: true });
  if (!c.finished)                bad('run did not finish');
  if (!near(c.step2, 30000, 200)) bad('step 2 did not start on time');
  if (!near(c.end, 50000, 200))   bad('run did not end on time');
  if (c.overruns.length)          bad('warned about an on-time run');

  // 4. Timers a minute late and no telemetry — e.g. a cool phase where the
  //    device has gone quiet. The run cannot be saved, so it must be reported.
  const d = await scenario('4. Timers 60s late, no telemetry (overrun must be reported)',
                           { throttleMs: 60000, telemetry: false, windowMs: 260000 });
  if (!d.finished)        bad('run never finished');
  if (!d.overruns.length) bad('overrun went unreported');
  if (d.end !== undefined && d.end <= 55000) bad('expected a badly overrun run, got ' + d.end + 'ms');

  // 5. Timer and telemetry can now both end a phase. Neither may double-apply.
  console.log('\n5. Double-advance guard');
  reset();
  throttleMs = 0;
  const api = build();
  makeRun(api, [{ volts: 2.0, dir: 'R', time: '0:10', cool: '0:00' },
                { volts: 3.0, dir: 'R', time: '0:10', cool: '0:00' },
                { volts: 4.0, dir: 'R', time: '0:10', cool: '0:00' }], 1);
  await api.appRunEnterPhase('run');
  await advance(40000, async () => {
    api.appRunCheckDeadline(); api.appRunCheckDeadline(); api.appRunCheckDeadline();
  });
  const v3 = sent.filter(s => s.cmd === 'SET_VOLTAGE:3.0').length;
  const v4 = sent.filter(s => s.cmd === 'SET_VOLTAGE:4.0').length;
  console.log(`  step 2 applied ${v3}x, step 3 applied ${v4}x (expected 1 each)`);
  if (v3 !== 1 || v4 !== 1) bad('a step was applied more than once');

  // 6. PAUSE stops the motor. Telemetry must not restart the program behind it.
  console.log('\n6. Paused run is not advanced by telemetry');
  reset();
  throttleMs = 0;
  const api2 = build();
  makeRun(api2, [{ volts: 2.0, dir: 'R', time: '0:10', cool: '0:00' },
                 { volts: 3.0, dir: 'R', time: '0:10', cool: '0:00' }], 1);
  await api2.appRunEnterPhase('run');
  await advance(2000);
  await api2.pauseAppProgram();
  await advance(60000, async () => { api2.appRunCheckDeadline(); });
  const advancedWhilePaused = sent.some(s => s.cmd === 'SET_VOLTAGE:3.0');
  console.log(`  advanced while paused: ${advancedWhilePaused} (expected false)`);
  if (advancedWhilePaused) bad('a paused run was advanced');

  console.log(fail ? `\n${fail} FAILURE(S)` : '\nALL PASS');
  // Not process.exit() — it truncates buffered stdout when piped, which made an
  // early version of this file report a silent clean pass with no output at all.
  process.exitCode = fail ? 1 : 0;
})().catch(e => {
  console.log('HARNESS ERROR:', (e && e.stack) || e);
  process.exitCode = 2;
});
