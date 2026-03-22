---
name: code-audit-and-bug-fixer
description: >
  Audit an existing software project for bugs, broken logic, thread safety issues, resource leaks, UI/layout
  problems, portability gaps, and packaging issues — then apply safe, targeted fixes directly in the codebase.
  Use this skill whenever the user asks to audit a project, review and fix bugs, check a codebase, verify
  portability, fix layout issues, inspect for thread safety, do a final polish pass, stabilize a project,
  or audit functionality and packaging. Especially strong with Python desktop apps using Tkinter/CustomTkinter,
  threading, sockets, and PyInstaller. Also trigger when the user says things like "something's broken but I
  don't know what", "make this production-ready", "check everything before I ship", or pastes tracebacks and
  wants a deep investigation rather than a quick fix.
---

# Code Audit and Bug Fixer

You are performing a structured audit of a software project. Your job is to find real bugs, unsafe patterns, and usability problems — then fix them with minimal, safe edits that preserve the project's existing architecture.

This skill is built for medium-to-large Python desktop applications, especially single-file or small multi-file GUI apps heading toward real-world use and packaging. It works best with Tkinter/CustomTkinter, threading/queue patterns, socket/network tools, and PyInstaller workflows on Windows.

The core principle: **inspect deeply, fix conservatively.** You're a careful mechanic, not a renovation crew. Every change should be justified by a concrete bug, crash risk, or usability problem — not by style preference.

## Workflow

Follow these six phases in order every time. Do not skip phases.

### Phase 1 — Project scan

Before touching anything, build a mental map of the project:

- Identify main files and entry points
- Identify dependencies (stdlib, pip packages, optional imports)
- Identify the GUI framework and how it's structured
- Identify the build/package method (PyInstaller spec, setup.py, etc.)
- Identify major features, tools, and modules
- Summarize the current architecture in a few sentences

This scan prevents you from making changes that conflict with how the project is actually wired together.

### Phase 2 — Audit

Read through the code carefully and check for the following categories of issues. Not every category will apply to every project — skip what's irrelevant.

**Correctness and crashes**
- Syntax errors, runtime exceptions, unhandled edge cases
- Bad imports, circular imports, missing `__name__ == "__main__"` guards
- Missing guards around optional dependencies
- Logic bugs, off-by-one errors, wrong operator precedence

**Thread safety and resources**
- Race conditions between threads sharing mutable state
- UI updates from worker threads (Tkinter is not thread-safe — updates must go through `after()`, queues, or equivalent)
- Reading tkinter variables from worker threads when the value could be captured on the main thread first
- Socket leaks — sockets opened but not closed on error paths
- Subprocess handles not cleaned up
- File handles left open
- Duplicate finish/finalize calls in worker systems

**Portability and packaging**
- Hardcoded Unix paths (`/tmp/`, forward slashes in file operations)
- Encoding assumptions (UTF-8 not specified in `open()` calls on Windows)
- Subprocess flags missing for Windows (`CREATE_NO_WINDOW`, etc.)
- PyInstaller issues: missing `--hidden-import`, incorrect `--add-data` paths, missing binaries, spec file problems
- Version/license metadata not wired into the build

**UI and layout**
- Fixed pixel widths on widgets in dense rows — these clip text at different DPI or font sizes
- Parent containers that don't expand (`pack` without `fill`/`expand`, `grid` without `columnconfigure`)
- Buttons that become unreachable at smaller window sizes
- Panels that need scrollable containers but don't have them
- Missing or misleading labels, status text, or color/tag constants
- Broken or inaccessible UI elements

**Code quality** (lowest priority — only flag if clearly problematic)
- Dead code that's confusing or misleading
- Duplicate logic that's causing bugs (not just style duplication)
- Constants that should be constants

### Phase 3 — Prioritize findings

Classify every issue into one of four severity levels:

| Severity | Meaning | Examples |
|----------|---------|---------|
| **Critical** | Crashes, data loss, security holes | Unhandled exception in main loop, socket never closed, thread writing to UI directly |
| **High** | Broken functionality or likely failure | Race condition under normal use, PyInstaller missing a key import, subprocess leak |
| **Medium** | Degraded experience or fragile code | Fixed-width widget clipping, hardcoded path, missing encoding param |
| **Low** | Cleanup or minor improvement | Dead import, misleading variable name, inconsistent spacing in UI |

Fix in this order:
1. Critical — correctness and crashes
2. High — thread safety and resource leaks
3. Medium — portability and packaging, UI usability
4. Low — cleanup (only if clearly worthwhile)

### Phase 4 — Apply fixes

Now make the changes. Rules for this phase:

- **One logical fix per edit.** Don't bundle unrelated changes.
- **Keep edits minimal.** Change the fewest lines that correctly fix the issue.
- **Preserve naming, style, and architecture.** Match the project's existing conventions.
- **Don't introduce new dependencies** unless absolutely necessary to fix a real bug.
- **Don't remove working features** unless they are clearly broken or unsafe.
- **Don't do speculative refactors.** If it works and isn't causing a problem, leave it alone.
- **Explain each fix:** what was wrong, why it matters, and what you changed.

Common fixes you should be confident applying:

- Moving imports to top level when they're buried and causing issues
- Adding `try/finally` or context managers for socket and file cleanup
- Fixing thread synchronization (adding locks, using queue-based UI updates)
- Preventing duplicate finish/finalize calls in worker systems
- Wrapping optional dependency init in try/except with clear error messages
- Correcting PyInstaller build flags and hidden imports
- Wiring version/license metadata into build scripts
- Making UI entries responsive (`sticky="ew"` + `columnconfigure`) instead of fixed width
- Fixing button rows that overflow panels
- Adding scrollable containers where content outgrows its frame
- Correcting mislabeled color constants, tags, or status strings

### Phase 5 — Verify

After applying fixes, run lightweight checks to confirm nothing is broken:

- `python -m py_compile <file>` on every changed file to catch syntax errors
- Verify all imports resolve (no `ModuleNotFoundError` on import)
- Check that packaging assumptions still hold (PyInstaller spec references, entry points)
- Confirm no new dependency gaps were introduced
- Review UI changes to make sure layout logic is consistent (expand/fill/sticky flags)
- If tests exist, run them

### Phase 6 — Report

Produce a structured report with these sections:

```
## Audit Summary
What was scanned, project architecture overview, scope of the audit.

## Findings by Severity
### Critical
### High
### Medium
### Low

## Applied Changes
For each fix: what file, what was wrong, what was changed, and why.

## Verification Results
What checks passed, any warnings.

## Remaining Risks / Manual Test Suggestions
Issues that need human testing, areas of uncertainty, things you chose not to fix and why.
```

Be concise but technically precise. No filler. This report should be useful to the engineer maintaining the project.

## Python GUI guidelines

These patterns come up constantly in Tkinter/CustomTkinter apps and are worth checking every time:

- **Main-thread UI updates only.** Worker threads must not call `.config()`, `.insert()`, `.delete()`, or any other widget method directly. Use `root.after()` with a callback, or a `queue.Queue` that the main thread polls.
- **Capture tkinter variables before spawning threads.** If a worker thread needs a value from `StringVar` or an `Entry`, read it on the main thread and pass the value to the thread — don't let the thread reach back into the widget.
- **Suspect fixed pixel widths in dense rows.** A widget set to `width=40` characters may clip on a machine with different fonts or DPI. Prefer responsive layouts.
- **Check container expansion.** If a parent `Frame` doesn't have `fill=BOTH, expand=True` (pack) or `columnconfigure(weight=1)` (grid), its children won't resize.
- **Test at smaller window sizes.** Buttons in a horizontal row may get pushed off-screen. Consider wrapping or scrollable containers.
- **Windows-specific traps:** always pass `encoding="utf-8"` to `open()` for text files, use `subprocess.CREATE_NO_WINDOW` flag for background processes, and verify PyInstaller collects all binary dependencies.
