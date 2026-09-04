---
name: claudlet
description: Launch/attach the claudlet desktop buddy, trigger a motion, configure it, or update it. "/claudlet" attaches a pet to the CURRENT session; "/claudlet standalone" launches an unattached roaming pet; "/claudlet <motion>" plays a motion (jump/wave/sing/juggle/float/celebrate/thinking/sleeping/error/attention); "/claudlet list" lists motions; "/claudlet stop" clears a held motion; "/claudlet config" shows/edits the user config (which motion shows for which activity, language); "/claudlet update" pulls the latest version and reinstalls. Use when the user types "/claudlet", "펫 띄워", "펫 붙여", "펫 점프", "펫 설정", "펫 커스터마이즈", "펫 업데이트", "update the pet", "start the pet", "configure the pet".
---

# claudlet — launch the desktop buddy

A frameless roaming pixel creature. By default this **attaches** a pet to the
**current session** (so it reacts to this session's Claude Code activity). Pass
`standalone` for an unattached one.

## How to run a claudlet command

claudlet ships console commands (`claudlet-attach`, `claudlet-motion`,
`claudlet-config`, `claudlet-version`, `claudlet-install`). Define this helper once, then use it in the sections
below — it prefers the installed command (pipx/pip put it on PATH) and falls
back to a source checkout's `bin/` shim:
```bash
cpet() {  # usage: cpet <subcmd> [args...]   e.g. cpet attach --standalone
  local name="claudlet-$1"; shift
  if command -v "$name" >/dev/null 2>&1; then "$name" "$@"
  elif [ -x "$HOME/claudlet/bin/$name" ]; then "$HOME/claudlet/bin/$name" "$@"
  else echo "claudlet isn't installed — see the README"; return 127; fi
}
```

## Routing

Look at the argument the user passed after `/claudlet`:

- a **motion name** (`jump`, `wave`, `sing`, `juggle`, `float`, `celebrate`,
  `thinking`, `sleeping`, `error`, `attention`), or `list`, or `stop`/`clear`
  → **Trigger a motion**; do NOT launch a pet.
- `config` (or `설정`; optionally `config open` / `config init`) → **Configure**;
  do NOT launch a pet.
- `update` (or `업데이트`) → **Update** (release channel). `update latest`
  (or `edge` / `develop`) → **Update** to the latest `develop` branch.
- `standalone` → **Standalone**.
- nothing → **Attach** (default).

## Attach (default)

```bash
cpet attach
```
`claudlet-attach` finds this session (`$CLAUDE_CODE_SESSION_ID`, else the
newest transcript under `~/.claude/projects/`), detects the host terminal/IDE
so click-to-focus targets the right window, skips if a pet is already attached
(the same liveness handshake the hook uses — a bare connect can't tell a live
pet from a reused stale port), and launches a detached pet bound to the session.
It prints `attached to session ...` or `already attached ...`.

**Reactions require hooks.** The pet only reacts to this session if the
claudlet hooks are installed (`claudlet-install`) AND this session loaded
them. If hooks were installed *after* this session started, restart the session
(or the pet attaches but stays idle). New sessions auto-attach their own pet via
the SessionStart hook, so `/claudlet` is mainly for sessions that predate the
install, or to bring a closed pet back.

## Standalone

An unattached, decorative pet that reacts to no particular session:
```bash
cpet attach --standalone
```

## Trigger a motion

```bash
cpet motion <arg>    # jump | wave | sing | juggle | float | celebrate | thinking | sleeping | error | attention | stop | list
```
e.g. `cpet motion jump`, `cpet motion float` (holds until `cpet motion stop`),
`cpet motion list`. It broadcasts to every running pet and prints how many
reacted; if it says `-> 0 pet(s)`, none is running — offer to attach one with
`/claudlet`.

## Configure

The user config remaps **which creature motion shows for which Claude Code
activity**, plus **language**. After a pipx install it's buried
(`~/.config/claudlet/config.json`, or `%USERPROFILE%\.config\claudlet\
config.json` on Windows), so use `claudlet-config` to locate/inspect it — never
guess the path.

```bash
cpet config          # show: absolute path, status, current values, IGNORED entries, valid values
cpet config init     # create a starter template if none exists
cpet config open     # open it in the OS default editor
```

`cpet config` prints the resolved absolute path and — crucially — any entries
that are **present in the file but silently dropped** (a typo'd state or unknown
slot) under `ignored:`. When something "doesn't work," check there first.

**Editing on the user's behalf.** When the user asks for a change in natural
language (e.g. "make it jump when I run Bash", "switch it to Korean"):
1. run `cpet config` to get the absolute path + current values,
2. `Read` that file (run `cpet config init` first if it's missing),
3. edit the JSON **directly with your own Edit/Write tools** using the schema
   below,
4. run `cpet config` again and confirm nothing landed under `ignored:`,
5. tell the user to **restart the pet** (right-click → 종료, then `/claudlet`)
   for it to apply — config is read at pet startup.

Schema (all keys optional; unknown keys / invalid values are dropped):
```json
{
  "lang": "auto",                        // "ko" | "en" | "auto"
  "tools":      { "Bash": "work_computer", "*": "work_computer" },
  "events":     { "prompt": "thinking", "celebrate": "juggle" },
  "raw_events": { "PostToolUse": "celebrate", "SubagentStop": "wave" },
  "dock": { "enabled": true, "anchor": "bottom-right",
            "screen": "primary", "gap": 4, "offset": {"x": 0, "y": 0} }
}
```
- `tools` — tool name → state (`"*"` = fallback for unmapped tools).
- `events` — event slot → state. Slots: `start`, `prompt`, `done`,
  `celebrate`, `error`, `permission`, `idle_prompt`, `asking`, `autopilot`.
- `raw_events` — raw hook event name → state (e.g. `PostToolUse`,
  `SubagentStop`, `PreCompact`).
- `dock` — where the pet stands. Docked is the DEFAULT: it holds a fixed corner
  slot instead of roaming, and several pets line up side by side (right to left,
  wrapping to another row) rather than overlapping. The user can drag a pet to
  move the whole row; the drop point is saved back here as `offset`, so a user
  asking for "another monitor" is usually better served by dragging than by
  guessing a `screen` index. `anchor`: `bottom-right` (default) / `bottom-left` /
  `top-right` / `top-left`. `screen`: `"primary"` or a monitor index.
  `enabled: false` restores the old roaming behaviour — same switch as the
  right-click menu's "자유롭게 돌아다니기" / "Roam freely".
  Note `roam_area` / `no_go` only bind a ROAMING pet; a docked one ignores them.
- Valid states (the `cpet config` output also lists these): `work_computer`,
  `work_search`, `work_web`, `work_agent`, `work_skill`, `thinking`,
  `celebrate`, `error`, `attention`, `asking`, `autopilot`, `sleeping`, `idle`,
  `jump`, `wave`, `sing`, `juggle`.

## Update

**This install is a customised fork** (`Rio-Kyeong/Claudlet`, branch `custom`).
It carries three things the upstream release does not, and the whole point is
that they survive every update:

1. pixel-grid rendering (no broken/shimmering art pixels),
2. click-to-focus that picks THIS session's JetBrains project window,
3. the project name printed under the pet.

So **never run `pipx install --force claudlet`** — that pulls the plain PyPI
release and silently throws all three away. The same goes for `pipx upgrade`.

**Do NOT run the update yourself.** It changes the user's environment and must be
followed by a session restart. Steps:

1. **Show current** (read-only, fine to run):
   ```bash
   cpet version
   ```
2. **Hand the user a `!`-prefixed command**, so it runs in their shell with the
   output visible:

   | | command |
   |---|---|
   | **reinstall the customised build** | `! claudlet-sync` |
   | **just reinstall, no upstream merge** | `! pipx install --force "git+https://github.com/Rio-Kyeong/Claudlet@custom" && claudlet-install` |

   `claudlet-sync` is the full path: it clones the fork, merges the latest
   upstream release into the `custom` branch, pushes, reinstalls and restarts the
   pets. If the merge conflicts it stops and says so rather than guessing — that
   means upstream changed the same lines as one of the three customisations, and
   a human has to reconcile them.

3. **Then reload**: the new hooks + pet code only take effect fresh. Tell them to
   close any running pet (right-click → 종료), **exit this session, and re-enter
   with `claude --continue`** (or start a new session).
4. **Setting this up on another machine or account**: one command, nothing else
   to copy — `pipx install "git+https://github.com/Rio-Kyeong/Claudlet@custom"`
   then `claudlet-install`.

## Notes
- Multiple pets are fine — each is independent. Stop one via right-click → 종료.
- This skill only launches/updates a pet; `claudlet-install` is what edits
  settings/hooks.
