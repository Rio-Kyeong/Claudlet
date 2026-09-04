"""claudlet-sync — update this customised build without losing the customisations.

This install is a fork whose `custom` branch carries three changes upstream does
not have (pixel-grid rendering, JetBrains project-window focus, the project-name
label). A plain `pipx install --force claudlet` pulls the PyPI release and throws
all three away, so updating has to go through the fork instead:

    clone the fork -> merge the latest upstream release into `custom` -> push ->
    reinstall from the branch -> reinstall hooks -> restart the pets

A merge conflict means upstream changed the same lines as one of the three
customisations. That needs a human, so this stops and says where, rather than
resolving it blindly.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

FORK = "https://github.com/Rio-Kyeong/Claudlet.git"
UPSTREAM = "https://github.com/YeeDochi/Claudlet.git"
BRANCH = "custom"


def _run(cmd, cwd=None, check=True, capture=True):
    p = subprocess.run(cmd, cwd=cwd, text=True,
                       stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.STDOUT if capture else None)
    if check and p.returncode != 0:
        raise RuntimeError("%s failed (%d)\n%s"
                           % (" ".join(cmd), p.returncode, p.stdout or ""))
    return (p.stdout or "").strip()


def _say(msg):
    print("[claudlet-sync] " + msg, flush=True)


def _stop_pets():
    """Stop every running pet. On Windows the venv's python.exe stays locked
    while a pet runs, and pipx then refuses to replace the venv."""
    stopped = 0
    if os.name == "nt":
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
              "Where-Object { $_.CommandLine -like '*-m claudlet*' } | "
              "Select-Object -ExpandProperty ProcessId")
        out = _run(["powershell", "-NoProfile", "-Command", ps], check=False)
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                subprocess.run(["taskkill", "/F", "/PID", line],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                stopped += 1
    else:
        out = _run(["pgrep", "-f", "-m", "claudlet"], check=False)
        for line in out.splitlines():
            if line.strip().isdigit():
                subprocess.run(["kill", "-9", line.strip()], check=False)
                stopped += 1
    return stopped


def _sessions_with_pets():
    """Session ids that had a pet, from the port files each pet leaves behind."""
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    out = []
    for name in os.listdir(base):
        m = re.match(r"claudlet-(.+)\.port$", name)
        if m:
            out.append(m.group(1))
    return out


def _handoff_script(sessions, restart):
    """Write the reinstall step as a script that runs AFTER this process exits.

    claudlet-sync runs from the pipx venv, so its own interpreter is
    `venvs/claudlet/Scripts/python.exe` -- the file pipx has to replace. On
    Windows that file is locked while we hold it, and pipx refuses with
    "Permission denied ... Not removing existing venv". So the reinstall cannot
    happen inside this process: it waits for our pid to disappear first.

    Returns (script_path, log_path).
    """
    tmp = tempfile.mkdtemp(prefix="claudlet-reinstall-")
    log = os.path.join(tmp, "reinstall.log")
    src = "git+%s@%s" % (FORK, BRANCH)
    attach = [["claudlet-attach", "--session", s] for s in sessions] if restart else []

    if os.name == "nt":
        lines = ["@echo off",
                 'powershell -NoProfile -Command "Wait-Process -Id %d '
                 '-ErrorAction SilentlyContinue" >nul 2>&1' % os.getpid(),
                 '(', 'echo === reinstall ===',
                 'pipx install --force "%s"' % src,
                 "echo === hooks ===", "claudlet-install"]
        lines += ["%s %s %s" % tuple(a) for a in attach]
        lines += [') > "%s" 2>&1' % log]
        path = os.path.join(tmp, "reinstall.cmd")
        cmd = ["cmd", "/c", "start", "", "/min", path]
    else:
        lines = ["#!/bin/sh",
                 "while kill -0 %d 2>/dev/null; do sleep 0.2; done" % os.getpid(),
                 "{ echo '=== reinstall ==='",
                 'pipx install --force "%s"' % src,
                 "echo '=== hooks ==='", "claudlet-install"]
        lines += [" ".join(a) for a in attach]
        lines += ["} > '%s' 2>&1" % log]
        path = os.path.join(tmp, "reinstall.sh")
        cmd = ["/bin/sh", path]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    if os.name != "nt":
        os.chmod(path, 0o755)
    return path, log, cmd


def _latest_upstream_ref(repo):
    """The newest upstream release tag, or upstream/master if there are none."""
    _run(["git", "fetch", "--tags", "upstream"], cwd=repo)
    tags = _run(["git", "tag", "--list", "v*", "--sort=-v:refname"], cwd=repo)
    for t in tags.splitlines():
        if t.strip():
            return t.strip()
    return "upstream/master"


def main(argv=None):
    # ASCII only: a Windows console on a Korean locale is cp949, and argparse
    # writing an em dash there raises UnicodeEncodeError instead of printing help
    ap = argparse.ArgumentParser(
        prog="claudlet-sync",
        description="Update this customised claudlet build (fork branch "
                    "'%s') without losing the customisations." % BRANCH)
    ap.add_argument("--ref", help="upstream ref to merge (default: newest release tag)")
    ap.add_argument("--develop", action="store_true",
                    help="merge upstream/develop instead of the newest release")
    ap.add_argument("--no-merge", action="store_true",
                    help="skip the upstream merge; just reinstall the branch")
    ap.add_argument("--no-restart", action="store_true",
                    help="leave the pets stopped instead of reattaching them")
    args = ap.parse_args(argv)

    if not shutil.which("git"):
        _say("git is not on PATH — cannot update the fork.")
        return 1
    if not shutil.which("pipx"):
        _say("pipx is not on PATH — is this a pipx install?")
        return 1

    tmp = tempfile.mkdtemp(prefix="claudlet-sync-")
    repo = os.path.join(tmp, "Claudlet")
    try:
        if not args.no_merge:
            _say("cloning the fork (%s)" % BRANCH)
            _run(["git", "clone", "--quiet", "--branch", BRANCH, FORK, repo])
            _run(["git", "remote", "add", "upstream", UPSTREAM], cwd=repo)
            ref = args.ref or ("upstream/develop" if args.develop
                               else _latest_upstream_ref(repo))
            _run(["git", "fetch", "--quiet", "upstream"], cwd=repo)
            before = _run(["git", "rev-parse", "HEAD"], cwd=repo)
            _say("merging %s" % ref)
            merge = subprocess.run(["git", "merge", "--no-edit", ref], cwd=repo,
                                   text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
            if merge.returncode != 0:
                _say("MERGE CONFLICT — upstream touched the same lines as one of "
                     "the customisations. Nothing was installed or pushed.")
                print(merge.stdout)
                _say("resolve it by hand in a checkout of %s (%s), then rerun."
                     % (FORK, BRANCH))
                return 2
            after = _run(["git", "rev-parse", "HEAD"], cwd=repo)
            if before == after:
                _say("already up to date with %s" % ref)
            else:
                _say("pushing the merge")
                _run(["git", "push", "origin", BRANCH], cwd=repo)

        sessions = _sessions_with_pets()
        n = _stop_pets()
        _say("stopped %d pet process(es)" % n)

        _script, log, cmd = _handoff_script(sessions, not args.no_restart)
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                         if os.name == "nt" else 0,
                         start_new_session=(os.name != "nt"))
        _say("reinstall handed off (it waits for this process to exit)")
        _say("log: %s" % log)
        _say("give it ~30s, then check `claudlet-version` and restart your "
             "Claude Code sessions so they load the new hooks.")
        return 0
    except RuntimeError as exc:
        _say("failed: %s" % exc)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _cli():
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    _cli()
