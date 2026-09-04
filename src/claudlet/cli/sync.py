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

        _say("reinstalling from the fork")
        _run(["pipx", "install", "--force", "git+%s@%s" % (FORK, BRANCH)],
             capture=False, check=True)
        _say("reinstalling hooks + skill")
        _run(["claudlet-install"], capture=False, check=False)

        if not args.no_restart:
            for sid in sessions:
                subprocess.run(["claudlet-attach", "--session", sid],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _say("reattached %d pet(s)" % len(sessions))

        _say("done. Restart your Claude Code sessions so they load the new hooks.")
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
