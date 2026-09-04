import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from claudlet.platform import jetbrains

from harness import pet, send_hook  # noqa: F401  (`pet` used as a fixture)

CWD = r"C:\Users\YYC\IdeaProjects\bnk-approval-fe"


def test_hook_cwd_names_the_pets_project(pet):
    send_hook(pet, "PreToolUse", session="a", tool_name="Bash", cwd=CWD)
    pet._tick()
    assert pet.snapshot()["project"] == "bnk-approval-fe"


def test_project_shows_up_in_the_pets_label(pet):
    send_hook(pet, "PreToolUse", session="a", tool_name="Bash", cwd=CWD)
    pet._tick()
    who = pet._who()
    assert "bnk-approval-fe" in who
    assert who.startswith("claudlet")


def test_label_falls_back_to_plain_when_the_project_is_unknown(pet):
    pet.project = None
    assert pet._who().startswith("claudlet — ")


def test_a_later_cwd_moves_the_pet_to_the_new_project(pet):
    send_hook(pet, "PreToolUse", session="a", tool_name="Bash", cwd=CWD)
    pet._tick()
    send_hook(pet, "PreToolUse", session="a", tool_name="Bash",
              cwd=r"C:\Users\YYC\IdeaProjects\serafin_v2_be")
    pet._tick()
    assert pet.snapshot()["project"] == "serafin_v2_be"


def test_project_window_is_picked_off_the_ide_titles(pet):
    # one process, four project windows: the pet must raise ITS project's window,
    # not whichever one the pid lookup happened to reach first
    windows = [(1712316, "bnk-approval-fe – 01_민원관리.md"),
               (4394156, "serafin [C:/Users/YYC/IdeaProjects/serafin_v2_be]")]
    raised = []

    class FakeGeom:
        def window_pid(self, _hwnd):
            return 36048

        def pid_window_titles(self, pid=None):
            return windows if pid == 36048 else []

        def activate_hwnd(self, hwnd):
            raised.append(hwnd)

    pet.host = "jetbrains"
    pet._cwd = r"C:\Users\YYC\IdeaProjects\serafin_v2_be"
    assert pet._focus_jetbrains_project(FakeGeom(), 1712316) is True
    assert raised == [4394156]


def test_non_jetbrains_host_keeps_the_pid_target(pet):
    class FakeGeom:
        def window_pid(self, _hwnd):
            raise AssertionError("must not be consulted for a non-JetBrains host")

    pet.host = "vscode"
    pet._cwd = CWD
    assert pet._focus_jetbrains_project(FakeGeom(), 123) is False


def test_unknown_project_keeps_the_pid_target(pet):
    class FakeGeom:
        def window_pid(self, _hwnd):
            return 36048

        def pid_window_titles(self, _pid=None):
            return [(1, "some-other-project – x.java")]

        def activate_hwnd(self, _hwnd):
            raise AssertionError("must not raise an unmatched window")

    pet.host = "jetbrains"
    pet._cwd = r"C:\Users\YYC\IdeaProjects\not-open"
    assert pet._focus_jetbrains_project(FakeGeom(), 1) is False


def test_falls_back_to_every_window_when_no_ancestor_owns_one(pet):
    # a pet started by hand has no live launching shell, so neither the pid
    # target nor the ancestor chain finds a window; the project title still does
    raised = []

    class FakeGeom:
        def window_pid(self, _hwnd):
            return None

        def pid_window_titles(self, pid=None):
            if pid is None:                     # desktop-wide enumeration
                return [(1, "Some Editor"), (77, "proj [C:/x/proj]")]
            return []

        def activate_hwnd(self, hwnd):
            raised.append(hwnd)

    pet.host = "jetbrains"
    pet._cwd = r"C:\x\proj"
    pet._ancestor_pids = [999]
    assert pet._focus_jetbrains_project(FakeGeom(), None) is True
    assert raised == [77]


def test_falls_back_to_an_ancestor_that_owns_windows(pet):
    # no pid-pinned window (minimized IDE, or a pet started without
    # --claude-pid): walk the ancestor chain for the process that owns windows
    raised = []

    class FakeGeom:
        def window_pid(self, _hwnd):
            return None

        def pid_window_titles(self, pid=None):
            return [(55, "proj – a.java")] if pid == 36048 else []

        def activate_hwnd(self, hwnd):
            raised.append(hwnd)

    pet.host = "jetbrains"
    pet._cwd = r"C:\x\proj"
    pet._ancestor_pids = [999, 36048]
    assert pet._focus_jetbrains_project(FakeGeom(), None) is True
    assert raised == [55]


def test_project_name_helper_matches_what_the_pet_stores(pet):
    assert jetbrains.project_name(CWD) == "bnk-approval-fe"


def test_cwd_given_at_launch_beats_the_transcript(monkeypatch):
    # a brand-new session has no transcript on disk, so the launcher's --cwd is
    # the only thing that can name the project at startup
    from claudlet import pet as P

    monkeypatch.setattr(jetbrains, "cwd_from_transcript",
                        lambda *a, **k: pytest.fail("must not be consulted"))
    p = P.Pet(session_id="brand-new", host="jetbrains", cwd=CWD)
    try:
        assert p.project == "bnk-approval-fe"
        assert p._cwd == CWD
    finally:
        p._cleanup()


def test_without_cwd_it_still_reads_the_transcript(monkeypatch):
    from claudlet import pet as P

    monkeypatch.setattr(jetbrains, "cwd_from_transcript", lambda *a, **k: CWD)
    p = P.Pet(session_id="older", host="jetbrains")
    try:
        assert p.project == "bnk-approval-fe"
    finally:
        p._cleanup()
