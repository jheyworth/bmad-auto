# D4 — tmux send-sequence smoke test findings

## Environment

- `tmux -V`: `tmux 3.6a`
- Binary path: `/opt/homebrew/bin/tmux`
- Platform: macOS (Darwin 25.5.0, Apple Silicon)
- Probe date: 2026-05-25
- Default pane geometry observed: `80x24`

## Verdict

**PASS** — primary path (`load-buffer` → `paste-buffer` → `send-keys C-m`) works
as written in SKILL.md stage 5.2.7. Byte-exact transmission confirmed. The
fallback path (`send-keys "$(cat …)" C-m`) was also exercised opportunistically
and is byte-exact as well; it is **not** under formal D4 test (per the picker
note, fallback is only exercised when `load-buffer` is unavailable, which it is
not on this system).

## Sequence exercised (primary path)

```sh
tmux new-session -d -s bmad-validate-tmux-probe cat
tmux load-buffer /tmp/bmad-validate-tmux-probe.txt
tmux paste-buffer -t bmad-validate-tmux-probe
tmux send-keys -t bmad-validate-tmux-probe C-m
tmux capture-pane -p -S -200 -t bmad-validate-tmux-probe
tmux kill-session -t bmad-validate-tmux-probe
```

All three send-sequence commands returned exit 0. No fallback was triggered.

## Buffer shape

Source buffer: 19 lines / 1772 bytes, modeled after a real `/goal` condition:

- Opens with `/goal Story 3-2 of epic 3 has \`status: done\`…`
- 4 paragraphs of autonomous-mode directives
- Embedded single quotes, double quotes, backtick-fenced code spans
- A full triple-backtick code-fence block containing `tmux load-buffer`,
  `tmux paste-buffer`, `tmux send-keys` calls (recursive content — the payload
  describes the very mechanism that delivers it)
- Embedded directive tokens: `[autonomous mode]`, `--dangerously-skip-permissions`,
  `--per-story-codex`, `intent_gap`, `VCS dirty`, `HALT`, `[end-of-goal]`

## Fidelity verification

Two independent fidelity checks were performed:

### Check 1: capture-pane (visual)

`tmux capture-pane -p -S -200` against the `cat` session shows the full buffer
echoed back, with one significant rendering artifact described below. The
captured pane is saved to `captured-pane.txt` in this directory.

### Check 2: byte-exact stdin-to-stdout (definitive)

To eliminate `capture-pane` rendering noise, the probe was re-run with
`cat > /tmp/bmad-validate-tmux-probe-catout.txt` so the bytes `cat` received
on stdin were written verbatim to a file. Compared against the source buffer:

- Source:   19 lines / 1772 bytes
- Received: 20 lines / 1773 bytes
- `diff`:   exactly one trailing newline added at the end (the `C-m`)

That is byte-exact transmission. The `paste-buffer` mechanism preserves all
line breaks, quotes (single and double), backticks, code-fence markers, em-
dashes (U+2014 used in the buffer), and embedded directives verbatim.

The fallback path was also tested for comparison and produced 19 lines /
1772 bytes received (the `$(cat …)` form strips the source's trailing
newline before `send-keys` appends `C-m`, hence -1 vs primary). Both paths
are functionally equivalent for `/goal` consumption.

## Caveats

### Capture-pane rendering artifact (cosmetic only)

The `tmux capture-pane` output for the primary path shows what appears to be
the buffer pasted twice with interleaved fragments — e.g. line 18 of the
captured output reads `cond/goal Story 3-2 of epic 3 has…` (fusing the tail of
"~45 seconds" from paragraph 2 with the start of the buffer), and line 34
shows `…within ~4aste-buffer -t auto-3-2…` (fragment of Directive 2 colliding
with a line from the embedded code-fence).

This is a **`capture-pane` scrollback rendering artifact**, not a transmission
defect. The receiving process (`cat`) saw byte-exact input (Check 2 above).
The artifact arises because `cat` echoes 80-column-wrapped stdout while
`paste-buffer` is still writing more bytes to stdin; tmux's screen buffer
interleaves the rapid bi-directional traffic non-deterministically in its
scrollback rendering. This will **not** affect the actual `/goal` payload that
the spawned `claude` process receives — `claude`'s readline reads the raw byte
stream, not tmux's captured screen.

If SKILL.md 5.2.7 or stage 5.2.8 ever relies on `capture-pane` output to
"verify the goal landed", it should not parse the captured text for byte-exact
buffer equality — it should instead check for a downstream signal (e.g. that
the spawned claude has emitted its own initial output, or that the story
status has advanced). Stage 5.2.8 already does the right thing: it greps the
captured pane for HALT tokens / story-status transitions, not for byte-exact
input echo.

### Terminal-width wrap

Lines longer than 80 columns are wrapped in the captured pane (e.g. the
opening `/goal Story…` paragraph wraps mid-word at column 80). This is normal
terminal behavior, not a fidelity issue. The bytes are unwrapped on the wire.

### Trailing newline behavior

- Primary path (`load-buffer` + `paste-buffer` + `send-keys C-m`): source
  ends with a final `\n` in the file; `C-m` appends an additional `\n` after
  the buffer. Net effect: receiving process sees source bytes + one extra
  `\n`. For `/goal` this is desirable — the final `\n` submits the prompt.
- Fallback path (`send-keys "$(cat …)" C-m`): `$(cat …)` strips the source's
  trailing `\n` (POSIX command substitution behavior), then `send-keys`
  appends `\n` from `C-m`. Net effect: receiving process sees source bytes
  minus the source trailing `\n` plus one `\n` from C-m. Functionally
  equivalent submission, but the absolute byte count differs by 1.

For `/goal`'s purposes both paths submit the prompt correctly. No SKILL.md
adjustment needed on this point.

## Recommendation for SKILL.md 5.2.7

**The documented sequence works as written. No change required.**

Specifically:

1. The three-command sequence `tmux load-buffer FILE` → `tmux paste-buffer -t
   SESSION` → `tmux send-keys -t SESSION C-m` is correct on tmux 3.6a.
2. The non-negotiable claim that this sequence is "robust to newlines and
   quotes" is empirically true (byte-exact in this probe).
3. The fallback path is also working today, so the SKILL's hedge ("if
   load-buffer/paste-buffer is unavailable for any reason") is sound — both
   paths are functional, the primary is preferred for its quote-robustness
   guarantees.
4. The `~2 second sleep between session spawn and send` (SKILL.md 5.2.6 →
   5.2.7) was preserved here as `sleep 1–2` and was sufficient. No timing
   issue observed.

Optional non-blocking suggestion (parking lot, do **not** apply as part of D4):
SKILL.md 5.2.7's fallback documents `tmux send-keys "$(cat …)" C-m`. The
double-quoted `$(cat …)` form is correct for preserving newlines but is
fragile if the buffer contains literal `$` followed by a word — shell command
substitution can interpret it. A real `/goal` payload likely won't contain
shell-expansion-prone tokens, but if a future test catches one, the safer
form is `tmux send-keys "$(cat -- "${TMPDIR:-/tmp}/…")" C-m` with `--` (which
is what's effectively used here, no change observed). Flagging for a future
SKILL.md edit-pass, not D4's scope.

## Files referenced

- Source buffer (constructed and torn down): `${TMPDIR:-/tmp}/bmad-validate-tmux-probe.txt`
- Captured pane: `skills/bmad-auto/test-fixtures/tmux-probe/captured-pane.txt`
- This findings file: `skills/bmad-auto/test-fixtures/tmux-probe/findings.md`

## Teardown confirmation

- `tmux ls | grep bmad-validate-tmux-probe`: no probe session (clean)
- `/tmp/bmad-validate-tmux-probe*`: no probe temp files (clean)
