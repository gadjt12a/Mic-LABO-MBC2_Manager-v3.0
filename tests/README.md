# Tests

Run from the repo root:

    node tests/test_program_timing.js

Exit code 0 = pass, 1 = a test failed, 2 = the harness itself broke (usually a
function it lifts out of the frontend has been renamed).

## Why Node, in a Python project

These test the frontend, which is JavaScript. Node is needed to run them and to
syntax-check the page, but **nothing in the app requires Node** — it is a
developer tool only, not a dependency of the build or of the shipped package.
If Node is not installed, skip these; the app is unaffected.

Handy alongside them, since the frontend is one big `<script>` and a parse error
there kills every button on the page:

    node --check <(extracted script)

## How these work

The frontend is deliberately a single file with no module system, so there is
nothing to `require()`. Each test lifts the functions it needs **out of
`app/mbc2-dashboard.html` by name** and evaluates them against stubs. That means
they exercise the shipped code rather than a copy that can quietly drift from
it — but it also means renaming a function breaks the test. If that happens, fix
the `NAMES` list; do not delete the test.

## test_program_timing.js

Guards the break-in program runner's step timing.

Step timing is wall-clock (`appRun.endsAt`), not `setTimeout` alone, because
browsers throttle timers in a hidden or occluded window — Chrome aligns them to
roughly one-minute wake-ups after five minutes hidden. That timer is what *ends
a step*, so relying on it runs the motor past the programmed time and the
session record shows a clean run of a program it did not follow.

A fake clock lets a 30-second step be tested instantly and can make timers fire
late or not at all. Six scenarios:

| # | Scenario | Expected |
|---|---|---|
| 1 | Visible window, accurate timers | steps at exactly 30000 / 50000 ms, no warning |
| 2 | Timers dead, no telemetry check | run stalls — reproduces the original bug on purpose |
| 3 | Timers dead, telemetry flowing | steps on time (the fix) |
| 4 | Timers 60 s late, no telemetry | finishes, and reports the overrun |
| 5 | Timer and telemetry racing | each step applied exactly once |
| 6 | Paused run | telemetry does not advance it |

Scenario 2 asserts a *failure*. It is there so the bug being guarded against
stays visible, and it will start failing if the check is ever made unconditional.

Verified to have teeth: with `appRunCheckDeadline()`'s advance removed, this
reports 3 failures and exits 1.
