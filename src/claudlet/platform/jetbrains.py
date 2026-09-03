"""Pick THIS session's JetBrains project window out of the IDE process.

A JetBrains IDE runs every open project in ONE process, so pid-ancestry — which
is all click-to-focus has to go on — identifies the IDE but not the project: a
user with four projects open gets whichever window EnumWindows reached first,
and clicking any pet raises the same one. Same shape as the Konsole/Windows
Terminal tab problem (`konsole.py`, `winterm.py`), and solved the same way: pid
gets us the process, then something process-specific picks our slot out of it.

Here that something is the window title, which carries the project. Two forms
show up, and both are needed:

    serafin [C:/Users/YYC/IdeaProjects/serafin_v2_be]   full path
    bnk-approval-fe – 01_민원관리.md                     project, then the file

The first is decisive, and the only thing that works when the display name and
the folder differ ("serafin" vs `serafin_v2_be`). The second is matched on the
leading segment ONLY, compared whole: `bnk-approval` is a prefix of
`bnk-approval-fe`, so a substring test would hand each project the other's
window.

Pure, so it is tested with real titles as data. No Qt, no ctypes.
"""
import os
import posixpath

# spaced dashes and the bracketed suffix separate the project from the rest of
# the title; a bare hyphen never does, or `bnk-approval-fe` would split
_SEPARATORS = (" – ", " — ", " - ", " [")


def project_name(cwd):
    """Last path segment of `cwd` — the project folder — or None."""
    if not cwd:
        return None
    return posixpath.basename(cwd.replace("\\", "/").rstrip("/")) or None


def _norm(path):
    return path.replace("\\", "/").rstrip("/").casefold()


def _leading_segment(title):
    cut = len(title)
    for sep in _SEPARATORS:
        i = title.find(sep)
        if 0 <= i < cut:
            cut = i
    return title[:cut].strip()


def pick_window(cwd, windows):
    """hwnd of the window showing `cwd`, or None if unknown or ambiguous.

    `windows` is [(hwnd, title)] for the IDE process. Returning None on an
    ambiguous match is deliberate: leaving the pid-chosen window alone beats
    raising an arbitrary one of two candidates.
    """
    if not cwd or not windows:
        return None
    want = _norm(cwd)
    name = project_name(cwd)
    if not want or not name:
        return None

    by_path, by_name = [], []
    for hwnd, title in windows:
        if not title:
            continue
        if want in _norm(title):
            by_path.append(hwnd)
        elif _leading_segment(title).casefold() == name.casefold():
            by_name.append(hwnd)

    for hits in (by_path, by_name):     # a spelled-out path outranks a bare name
        if len(hits) == 1:
            return hits[0]
        if hits:
            return None
    return None


def focus(cwd, enum_windows, activate):
    """Raise the window showing `cwd`; return the hwnd, or None if not found.

    `enum_windows` -> [(hwnd, title)] for the IDE process, `activate` raises one.
    Both injected so the decision stays testable without a desktop. Best-effort:
    a failing enumerator leaves the caller's pid-chosen target in place.
    """
    try:
        windows = enum_windows()
    except Exception:
        return None
    hwnd = pick_window(cwd, windows)
    if hwnd is None:
        return None
    try:
        activate(hwnd)
    except Exception:
        return None
    return hwnd


def cwd_from_transcript(session_id, projects_dir=None, read_lines=None):
    """This session's working directory, read off its Claude Code transcript.

    The pet needs the project before any hook event arrives (a pet attached
    mid-session would otherwise have nothing to match on), and the transcript is
    the only source available then. The directory name under `projects` is the
    cwd with separators flattened to '-', which is not reversible — `-` also
    occurs inside folder names — so the exact path is read from a `cwd` field
    inside the file instead.

    `read_lines` is injected for tests; it takes a path and yields text lines.
    """
    import glob
    import json

    if not session_id:
        return None
    base = projects_dir or os.path.expanduser("~/.claude/projects")
    hits = glob.glob(os.path.join(base, "*", session_id + ".jsonl"))
    if not hits:
        return None

    def _default_reader(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line

    reader = read_lines or _default_reader
    try:
        for i, line in enumerate(reader(hits[0])):
            if i > 200:                  # cwd shows up in the first few lines
                break
            try:
                cwd = json.loads(line).get("cwd")
            except (ValueError, AttributeError):
                continue
            if cwd:
                return cwd
    except OSError:
        return None
    return None
