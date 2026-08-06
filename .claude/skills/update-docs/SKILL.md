---
name: update-docs
description: Bring the MBC2 Dashboard docs back in line with the code after a change. Use when the user says "update docs", "/update-docs", "document this", or after landing a feature, fix or architectural change that the docs do not yet reflect.
---

# Update the docs

Each doc has a different audience. Writing the same paragraph into all of them
is the failure mode — decide what each one needs, and skip the ones that do not
need anything.

| Doc | Audience | Put here |
|---|---|---|
| `CHANGELOG.md` | someone diffing versions | what changed, factually, under Added / Changed / Fixed |
| `RELEASE_NOTES_v4.md` | a club member downloading it | why they should care, in plain English, no internals |
| `README.md` | someone deciding whether to use it | feature list, requirements, how to run — only if those changed |
| `docs/FEATURE_ROADMAP.md` | future planning | open issues, proposals, and phases as they complete |
| `DEPLOYMENT_PLAN.md` | the v4 release effort | phase status, test matrix rows, build/risk notes |
| `CLAUDE.md` | the next Claude session | facts a fresh session would otherwise get **wrong** |
| `BUILD.md` | whoever cuts the next build | build steps, interpreter/tool versions, release build record |
| `docs/SERIAL_SPEC.md`, `docs/DB_SCHEMA.md` | protocol/schema reference | only when the wire format or schema actually changed |

## How to do it

1. **Find what is undocumented.** `git log --oneline` since the last docs
   commit, plus `git status`. Work from what the code actually does, not from
   the commit messages alone.

2. **Verify before you write.** Read the code for anything you are about to
   assert. This repo has burned a session on exactly this: after serial moved
   from the browser into Python, every user-facing doc still promised a
   Chrome-only Web Serial app, and `CLAUDE.md` still carried a "no native
   window — ever" hard rule that the shipped code contradicted.

3. **Hunt stale claims, not just missing ones.** Grep the docs for terms tied
   to what changed and check each hit still holds. A doc that is confidently
   wrong costs more than one that is merely incomplete.

4. **Write the entries.** Lead with the change and its consequence. Skip
   internals in `RELEASE_NOTES` and `README`; keep them in `CHANGELOG`.

5. **Check memory for staleness.** Read `MEMORY.md` and any memory file
   touching what changed. Memory is not a second changelog — do not write the
   change into it. The job is only to correct entries the change has made
   wrong, and delete ones it has made obsolete. Memory files are dated
   snapshots, so a stale one actively misleads: the `v4-packaging-plan` memory
   once read "plan drafted, work not started" while phases 1–4.7 were
   complete. Anything the repo now records belongs in the repo, not here.

6. **Commit and push** with a message saying which docs changed and why.
   Memory lives outside the repo and is not part of that commit.

## Rules

- **Never mark something verified that has not been.** If a feature is only
  syntax-checked, say so and carry the caveat into the docs. Hardware-tested
  and "it builds" are different claims.
- **Do not rewrite history.** Old `CHANGELOG` entries describe what was true
  then — the v1.0 Web Serial entry stays. Correct current-state docs instead.
- **Withdraw superseded rules explicitly**, with the reason they existed. A
  silently deleted hard rule looks like an oversight and gets reinstated.
- **`CLAUDE.md` earns its keep on traps, not summaries.** Write the thing a
  fresh session would get wrong: which of two similar structures is which,
  which conversion to suspect first, which guard must not be removed. Do not
  restate what the code plainly shows.
- Respect the hard rules in `CLAUDE.md` while editing — especially that the
  frontend stays a single file, and that Christchurch club programs (PMPE,
  SPRF) never appear in any shipped seed data or example.
- Keep `docs/FEATURE_ROADMAP.md` honest: resolved items move out of "Open
  issues" into a completed phase; unresolved ones stay, with their evidence.
