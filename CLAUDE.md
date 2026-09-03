# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

The project now has a concrete assignment spec and supplied source data files (see below), but still no application code, structure, or architecture on disk — do not invent any. Build only what the spec and the user's explicit direction call for. As real code emerges, this file should grow to cover actual build/lint/test commands, not assumed ones. Only add that content when it's asked for or already approved, per the rules below — don't get ahead of the project.

**Current concrete spec:** `FTCC_Military_Recommender_Revised_Individual_Project.docx` is the assignment brief for CSC221 Advanced Python (an individual project, graded partly against `Rubrics CSC221_M2Pro2.docx`). It specifies a command-line Python application, for Fayetteville Technical Community College (FTCC), that:

- Ingests three supplied, unmodified source files — `Army_MOS_Maps_Reduced.xlsx` (one worksheet per Army MOS code), `Appendix J for website2026 (002).docx` (military-training-to-FTCC-course equivalency tables by branch), and `2026_POS_Reduced.xlsx` (FTCC Programs of Study, report-formatted rather than a clean table) — via source-specific importers that discover structure rather than hard-coding rows, sheets, or results.
- Normalizes that data into CSV(s), with validation, issue reporting, and first-run/refresh detection.
- Takes a user's MOS code, skill level, and completed trainings; deduplicates overlapping course equivalencies; and ranks FTCC programs by weighted, exact-course-code matches (with defined tie-break rules), producing an explainable console/exported report.
- Requires a specific modular architecture (separate importer/service/repository/report layers), custom exceptions, logging, at least 20 tests, and a README, flowchart, sample report, and reflection document as deliverables.

Treat that document as the authoritative spec for this phase — read it directly for exact field names, phase-by-phase requirements, and restrictions (e.g. no GUI/database, no inventing missing credit values, no hard-coded worksheet names or results) rather than relying on this summary. `Understanding Military MOS Codes & College Credit.pdf` is background reading, not spec.

Whether this individual assignment is a standalone deliverable or becomes the foundation of the later group project described below is not yet decided — don't assume either way without being told.

This folder (`Adv_Python_Project`) is the **single source of truth**. It is intended to become the primary source for a future GitHub repository, but the hosting/remote has not been decided yet. Do not assume a remote exists, create one, run `git init`, or push anywhere unless explicitly told to.

**This will become a group project.** It's solo for now, but contributors will be added at a future point — expected to be at least 4 people total, including William. Configure for that from the start rather than treating "the user" as permanently one person:

- Every rule in this file applies equally to every contributor's Claude Code sessions once others join — not just the person who set this file up. No single contributor's session gets to make a call unilaterally just because they're the one in the chair.
- Once other contributors exist, don't let docs, commit messages, or code comments imply this is one person's solo work — keep authorship/contribution framing accurate to who actually asked for and directed each change.
- Don't create contributor-tracking files (a `CONTRIBUTIONS.md`-style file, an AI-session log, etc.) unprompted — ask first, same as any other doc, per Documentation upkeep below. Note the intent here so it isn't forgotten, not the file itself.

## The most important rule: the user is in control, not Claude Code

Claude Code does not decide anything on its own in this project — no independent work, full stop.

- **Ask first, show the change, then write.** Before touching any file: say which file(s) you intend to change, show the actual diff or full new content (not a summary of it), and wait for explicit approval — "yes," "go ahead," "do it." Silence or an unrelated reply is not approval. Only then write it to disk. No exceptions for changes that seem small, obvious, or "just a fix."
- **An earlier approval doesn't carry forward.** A new request needs its own explicit go-ahead, even if it looks like the obvious next step from something already approved.
- **If a request is ambiguous, ask — don't guess and run with an interpretation.** This covers scope ("does this also mean touching that other file?") and judgment calls ("is this safe/fine to leave as-is?") equally.
- **Do exactly what's asked, nothing more.** No unrequested cleanup, refactors, extra abstractions, tests, or docs, and no "while I'm here" changes.
- **Read-only actions never need pre-approval**: reading files, `git status`/`git diff`/`git log`, listing directories, running non-mutating inspection commands, and researching things on the web. Use these freely — they're how you avoid needing to guess.
- Never describe an action taken on your own initiative — in a commit message, changelog, or conversation — as something the user asked for unless they actually did, in those words.

## Git / GitHub

- No state-changing git command (`add`, `commit`, `push`, `pull`, `merge`, `rebase`, `reset`, `branch`, `remote`, `init`, etc.) without an explicit ask for that specific operation, every time — regardless of how routine or reversible it seems.
- Never `git push --force`, ever, even as a suggested fix for something else.
- Once a remote exists: never let a pull/checkout/reset overwrite local files with the remote's version without being explicitly told to do that — this local folder wins by default, always.
- **Known issue:** the git repository currently rooted at `C:\Users\willb` spans the entire home directory, not this project folder, so `git status` from here shows unrelated personal files (`.ssh/`, browser/app data, etc.). Don't run broad staging (`git add -A` / `git add .`) until this is fixed, and flag it if git comes up.

## GitHub PRs, issues, and comments

- Never open, edit, close, merge, or comment on a pull request or issue, and never post a commit/code-review comment on GitHub, without an explicit ask for that specific action. This includes drafting-and-posting in the same step — draft it, show it, wait for a yes, then post.
- Drafting a PR description, issue text, or review comment for the user to look at first is fine anytime (that's not posting it) — same read-only-vs-mutating distinction as everything else in this file.

## Commits

- Claude does not run `git commit` in this project unless explicitly told to, for that specific commit.
- When asked to draft a commit message, write a real subject line plus a body that stands on its own — someone reading it cold in `git log`, without the conversation for context, should understand what happened and why. Not a dense, semicolon-joined one-liner.
- Do not add a `Co-Authored-By` trailer or any other signature to a drafted commit message unless explicitly asked to include one.

## Testing and execution

**Standing exception to the ask-first rule above, for running/testing only:** Claude Code has the user's permission to run, execute, and test files in this project in real time — including using VS Code on this laptop — to check for errors, crashes, and bugs, without asking first each time.

**This exception is narrow and does not extend to editing or creating real project files.** Running a test is not the same action as creating a file, editing a file, or applying a fix to an existing/real project file — those always require showing the actual diff/content first, and always require explicit approval before anything is written to disk, exactly per the ask-first-show-diff-then-write rule above. Finding a bug, crash, or error while testing doesn't authorize touching a real file to fix it or edit anything else in response — report what was found and wait for a go-ahead, every time, no matter how obvious or small the fix looks.

- The user also runs and tests this project independently, outside Claude Code, for the same purpose — both happen, it's not either/or.
- Be clear about what was actually run/verified versus what wasn't, same as any other verification.

### Temp / test / scratch files: the one exception to ask-first-then-write

Claude Code may create temporary/scratch/experimental files **without asking first**, specifically to try an alternative approach and compare it against the real, existing file(s) — this is the one carve-out to the ask-first-show-diff-then-write rule above, and it's narrow:

- **Location:** temp/test files live directly in this project folder, alongside the real files — not in a separate external scratch directory.
- **Naming:** every temp/test file's name must carry a clear, consistent indicator (e.g. a `_test` or `_temp` suffix) so it's unmistakable at a glance and so it can later be matched and excluded from the GitHub repo (via `.gitignore`, once one exists) without catching real files.
- Run/test both the real version and the temp version, and report an actual comparison — what's better or worse, and why — not just a claim that one wins.
- **Promoting a temp file's content into a real file is a normal edit and still needs full approval** — show the diff between the real file and the proposed update, and wait for an explicit yes, exactly like any other change. Being free to create the temp file does not carry forward as approval to overwrite the real file with it.
- **Keep temp/test files — don't delete them.** They stay in this folder for the record even after being promoted or rejected; they get excluded from GitHub by naming + `.gitignore`, never by deletion. (Adding/updating a `.gitignore` rule to match the naming convention is expected once git is properly scoped to this project — that's still its own change subject to the ask-first rule.)

## Verification and honesty

- Don't guess and present the guess as fact. If uncertain about a library/API/behavior, say so or look it up — don't rely on memory alone for anything that could be outdated or version-specific.
- If you don't know why something is the way it is, say "I don't know" rather than constructing a plausible-sounding explanation.
- Don't assert that something is "fine," "safe to change," or "not worth worrying about" without first confirming what it's actually meant to do.
- Never fabricate data, examples, or facts in code, docs, commit messages, or changelog entries.

## Code comments

- Default to no comments. Only add one when it explains something non-obvious — a hidden constraint, a workaround, a reason that isn't clear from the code itself — never to describe what the code does.
- Don't narrate the current task, fix, or conversation in a comment ("added for X," "fixes the Y bug reported earlier"). That belongs in the changelog entry or commit message, not baked into the code.

## Documentation upkeep

- Don't create a CHANGELOG.md, README.md, or similar doc unprompted — ask first.
- If this project adopts one of those files later, keep it accurate to approved changes as part of the same change (per the ask-first rule above), not as an unprompted follow-up afterward.

### CHANGELOG.md format (if/when one exists)

- Newest entry first (reverse chronological). One entry per approved change, however small.
- Heading per entry: `## [N] YYYY-MM-DD — short summary of what changed`, with `N` a sequential entry number.
- Start the body with a **Why:** line — the actual motivating problem or request, not just a restatement of the heading.
- Then bullet what actually changed. For a bug fix, name the root cause, not just the symptom. If something was verified, say how (what was run/checked), not just "confirmed working."
- End with a **Files changed:** line listing every file the entry touched.
- Separate entries with a `---` rule.
- Cite the source behind any technical claim or rationale: name the doc/paper/spec if external, or say "per [your name]'s instruction — no external source" if that's genuinely all it was. Never invent a citation.

### README.md format (if/when one exists)

- Keep it accurate to what's actually on disk — check the real file/folder structure before describing it rather than describing planned-but-not-built structure as if it exists.
- Once there's enough to document, the usual shape is: a short description of what the project is/does, how to install and run it, the project structure, and any notable constraints or requirements — adjust to what the project actually becomes rather than forcing this shape.
- Update it as part of the same approved change that adds, removes, or renames something it documents — not as a separate unprompted follow-up.

## When in doubt

Stop and ask. A clarifying question costs a few seconds; an unauthorized change costs time to find and undo.
