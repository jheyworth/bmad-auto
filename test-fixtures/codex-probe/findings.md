# Codex CLI flag probe — findings

> Source for D8 ([bmad-auto-validate.md](../../../build-tasks/bmad-auto-validate.md))
> against SKILL.md stage 7.1.4. Probe performed against locally installed
> codex CLI. Companion verbatim capture lives in
> [help-output.txt](help-output.txt).

## Probe result

| Probe | Result |
| --- | --- |
| `command -v codex` | `/opt/homebrew/bin/codex` (exit 0) |
| `codex --version` | `codex-cli 0.124.0` |
| `codex --help` | exit 0, full help captured in `help-output.txt` |
| `codex review --help` | exit 0, full help captured in `help-output.txt` |

**Codex is present in this environment. D8 has substantive work to do
(see § "Recommendation for D8" below). It is NOT a no-op.**

## Real `codex review` flag surface

From `codex review --help` verbatim:

```
Usage: codex review [OPTIONS] [PROMPT]

Arguments:
  [PROMPT]
          Custom review instructions. If `-` is used, read from stdin

Options:
  -c, --config <key=value>   Override config (TOML)
      --uncommitted          Review staged, unstaged, and untracked changes
      --base <BRANCH>        Review changes against the given base branch
      --enable <FEATURE>     Enable a feature flag
      --commit <SHA>         Review the changes introduced by a commit
      --disable <FEATURE>    Disable a feature flag
      --title <TITLE>        Optional commit title to display in the review summary
  -h, --help                 Print help
```

### Required flags for adversarial review against a diff

The minimum-viable invocation depends on the diff shape:

| Diff shape | Invocation |
| --- | --- |
| Working-tree (staged + unstaged + untracked) | `codex review --uncommitted "<prompt>"` |
| HEAD vs. a branch (e.g. branch-since-cut-from-main) | `codex review --base <BRANCH> "<prompt>"` |
| A single commit | `codex review --commit <SHA> "<prompt>"` |
| Arbitrary `<start-sha>..<end-sha>` range | **Not natively supported.** See "structural gap" below. |

The prompt is a **positional argument**, NOT a `--prompt` flag. Passing
`-` as the positional reads the PROMPT from stdin (not the diff).

### Optional flags worth knowing

- `-c, --config <key=value>` — override config from `~/.codex/config.toml`
  with TOML-parsed values. Examples in `--help`: `-c model="o3"`,
  `-c 'sandbox_permissions=["disk-full-read-access"]'`.
- `--title <TITLE>` — optional commit title to display in the review
  summary. Cosmetic, but useful for distinguishing per-epic runs in the
  saved artifact.
- `--enable <FEATURE>` / `--disable <FEATURE>` — feature flag toggles
  (equivalent to `-c features.<name>=true|false`). Not currently
  needed for SKILL.md 7.1.4's adversarial-review use case.

### Streaming vs. buffered output

**Undocumented in `--help`.** No `--stream` / `--output-format` /
`--quiet` flag is present in the `codex review` flag list. D3's
no-real-invocation constraint prevents direct observation. D8 should
treat output as buffered for planning purposes; if streaming behavior
matters at G4, the operator can confirm during a real Path-A run.

### Piped-diff input support

**Not supported as `codex review` describes it.** The `-` stdin form is
for the PROMPT, not the diff. Real codex computes the diff itself from
one of `--uncommitted` / `--base` / `--commit` — it does not accept a
pre-computed `git diff` over stdin.

This is the **largest structural mismatch** between SKILL.md 7.1.4 and
real codex (see § "SKILL.md mismatches" below).

## SKILL.md mismatches

SKILL.md stage 7.1.4 currently documents the invocation as
(verbatim from SKILL.md line 417):

> `git diff <start-sha>..<end-sha> | codex review --stdin --prompt "<adversarial prompt above>"` (or whatever the `codex review --help` output indicates is correct)

Three distinct mismatches against real `codex review`:

| Aspect | SKILL.md 7.1.4 says | Real codex 0.124.0 |
| --- | --- | --- |
| Prompt input | `--prompt "<text>"` flag | Positional `[PROMPT]` argument |
| Stdin behavior | `--stdin` consumes piped diff | No `--stdin` flag; `-` positional reads prompt from stdin |
| Diff input shape | Pre-computed `git diff <start>..<end>` over stdin | Codex computes diff itself from `--uncommitted` / `--base <BRANCH>` / `--commit <SHA>` |

The runtime-introspection hedge (SKILL.md 7.1.4 step 4 says *"if the
actual flag spelling differs from what is described here, prefer what
--help reports over what is written here"*) catches the first two
mismatches — a runtime agent could match `--prompt` → positional and
might reasonably substitute. **It does NOT catch the third**, which is
not a flag-rename but a CLI-design gap: real codex has no input mode
that accepts an arbitrary `<start-sha>..<end-sha>` range. A runtime
agent reading the current SKILL.md and the real `--help` together
would emerge confused about how to feed a pre-computed git-diff range
to `codex review`.

## Recommendation for D8

D8 should hardcode the corrected flag set into SKILL.md 7.1.4 rather
than continuing to rely solely on the runtime-introspection hedge.
Concretely:

1. **Replace the pseudo-invocation example on line 417.** Current text:

   > `git diff <start-sha>..<end-sha> | codex review --stdin --prompt "<adversarial prompt above>"`

   Replace with:

   > `codex review --base <merge-base-branch> "<adversarial prompt above>"`

   …where `<merge-base-branch>` is the branch the feature branch was cut
   from (typically `main` or the operator's documented integration
   branch). For SHA-range input, see point 2.

2. **Document the SHA-range workaround.** SKILL.md 7.1.3's diff-range
   computation produces a `<start-sha>..<end-sha>` pair. Since real
   codex doesn't accept this shape, document the workaround: create a
   throwaway branch at `<start-sha>` (e.g. `git branch
   bmad-auto-codex-base-<runId> <start-sha>`), run
   `codex review --base bmad-auto-codex-base-<runId> "<prompt>"`, then
   delete the throwaway branch in cleanup. Note the branch creation in
   the saved `epic-K-codex-review.md` artifact so the operator can
   reproduce.

3. **Update Launch sub-step 5.2.11.1** if it currently describes the
   per-story Codex invocation with the same `--stdin --prompt`
   pattern. (D8's scope per the task list.)

4. **Keep the runtime-introspection hedge** as belt-and-suspenders.
   The hedge protects against future codex-cli releases changing the
   flag surface; hardcoding alone would lock against drift in the
   other direction. The two together — hardcoded best-known invocation
   plus introspection fallback — is the right design.

5. **Pin the verified codex version.** Document in SKILL.md 7.1.4
   that the hardcoded flags were verified against `codex-cli 0.124.0`.
   Future regressions are then diagnosable: an operator hitting a
   flag-name failure can compare their version against the pin and
   know whether the hedge should take over.

6. **Note streaming behavior is undocumented in --help.** D8 cannot
   resolve this without a real invocation; flag it for G4 to confirm.

## Re-verification protocol

To re-verify this probe in a future codex-cli release:

```sh
cd skills/bmad-auto/test-fixtures/codex-probe/
codex --version > /tmp/codex-version-new.txt
codex --help > /tmp/codex-help-new.txt
codex review --help > /tmp/codex-review-help-new.txt
diff -u <(grep -A 100 "codex --help" help-output.txt) /tmp/codex-help-new.txt
diff -u <(grep -A 100 "codex review --help" help-output.txt) /tmp/codex-review-help-new.txt
```

If either diff shows changes to the flag surface, re-examine the
"SKILL.md mismatches" table and update D8's hardcoded flag set
accordingly.

## What's notable

The deepest finding is **not** that SKILL.md has the flag names wrong
— it's that SKILL.md and real codex have **different mental models of
diff input**. SKILL.md assumes a Unix-pipe model (compute the diff in
the orchestrator, hand it to the reviewer), while real codex assumes a
git-native model (give the reviewer git refs and let it compute the
diff itself). The runtime-introspection hedge catches lexical drift but
not architectural drift. This is why D8 is non-trivial: it's not
search-and-replace flag names, it's reconciling two diff-input
philosophies. The synthetic-branch workaround in recommendation 2 is
the bridge — it converts SKILL.md's SHA-range output into the form
codex's mental model expects without changing 7.1.3's upstream
computation. Worth flagging for G4 reviewer awareness: if a future
codex release adds native `--range <A>..<B>` support, the workaround
becomes obsolete and SKILL.md should drop the throwaway-branch
ceremony.
