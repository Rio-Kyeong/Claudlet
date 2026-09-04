import claudlet.cli.sync as S


def test_points_at_the_fork_not_upstream():
    # a plain `pipx install --force claudlet` would drop every customisation;
    # the whole point of this command is that the install source stays the fork
    assert "Rio-Kyeong" in S.FORK
    assert "YeeDochi" in S.UPSTREAM
    assert S.BRANCH == "custom"


def test_latest_upstream_ref_prefers_the_newest_release_tag(monkeypatch):
    calls = []

    def fake_run(cmd, cwd=None, check=True, capture=True):
        calls.append(cmd)
        if cmd[:2] == ["git", "tag"]:
            return "v1.7.0\nv1.6.0\nv1.5.1"
        return ""

    monkeypatch.setattr(S, "_run", fake_run)
    assert S._latest_upstream_ref("/repo") == "v1.7.0"


def test_latest_upstream_ref_falls_back_to_master(monkeypatch):
    monkeypatch.setattr(S, "_run", lambda *a, **k: "")
    assert S._latest_upstream_ref("/repo") == "upstream/master"


def test_sessions_with_pets_reads_the_port_files(monkeypatch, tmp_path):
    (tmp_path / "claudlet-abc123.port").write_text("5000")
    (tmp_path / "claudlet-def456.port").write_text("5001")
    (tmp_path / "unrelated.txt").write_text("x")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert sorted(S._sessions_with_pets()) == ["abc123", "def456"]


def test_merge_conflict_stops_before_installing(monkeypatch, tmp_path):
    # a conflict means upstream changed the same lines as a customisation:
    # installing anyway would ship a half-merged tree
    installed = []
    monkeypatch.setattr(S, "_run", lambda *a, **k: "")
    monkeypatch.setattr(S, "_stop_pets", lambda: installed.append("stopped"))
    monkeypatch.setattr(S.tempfile, "mkdtemp", lambda prefix=None: str(tmp_path))

    class Fail:
        returncode = 1
        stdout = "CONFLICT (content): Merge conflict in src/claudlet/pet.py"

    monkeypatch.setattr(S.subprocess, "run", lambda *a, **k: Fail())
    assert S.main([]) == 2
    assert installed == []
