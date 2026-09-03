import json

from claudlet.platform import jetbrains as J

# Real titles taken off one idea64.exe hosting four project windows at once.
WINDOWS = [
    (1712316, "bnk-approval-fe – 01_민원관리.md"),
    (4394156, "serafin [C:/Users/YYC/IdeaProjects/serafin_v2_be]"),
    (2952498, "bnk-approval"),
    (199540, "serafin – AsLifecycleService.java [serafin.main]"),
]


def test_picks_window_by_path_in_title():
    # the display name ("serafin") differs from the folder ("serafin_v2_be"), so
    # only the path in the title identifies this one
    got = J.pick_window(r"C:\Users\YYC\IdeaProjects\serafin_v2_be", WINDOWS)
    assert got == 4394156


def test_picks_window_by_leading_project_segment():
    got = J.pick_window(r"C:\Users\YYC\IdeaProjects\bnk-approval-fe", WINDOWS)
    assert got == 1712316


def test_longer_project_name_is_not_absorbed_by_the_shorter_one():
    # "bnk-approval" is a prefix of "bnk-approval-fe": a substring match would
    # hand either project the other's window
    assert J.pick_window(r"C:\Users\YYC\IdeaProjects\bnk-approval", WINDOWS) == 2952498
    assert J.pick_window(r"C:\Users\YYC\IdeaProjects\bnk-approval-fe", WINDOWS) == 1712316


def test_module_name_in_brackets_is_not_a_path():
    # "[serafin.main]" is a module label; nothing may match it as a directory
    assert J.pick_window(r"C:\Users\YYC\IdeaProjects\serafin.main", WINDOWS) is None


def test_unknown_project_gives_no_answer():
    assert J.pick_window(r"C:\Users\YYC\IdeaProjects\not-open", WINDOWS) is None


def test_no_cwd_or_no_windows_gives_no_answer():
    assert J.pick_window(None, WINDOWS) is None
    assert J.pick_window("", WINDOWS) is None
    assert J.pick_window(r"C:\p", []) is None


def test_ambiguous_match_refuses_to_guess():
    # two windows for one project (IntelliJ can show the same project twice):
    # raising an arbitrary one is worse than leaving the pid target alone
    dupes = [(1, "proj – a.java"), (2, "proj – b.java")]
    assert J.pick_window(r"C:\x\proj", dupes) is None


def test_path_match_wins_over_a_name_only_match():
    # a name collision must lose to the window that spells out the real path
    wins = [(1, "proj – a.java"), (2, "proj [C:/other/proj]")]
    assert J.pick_window(r"C:\other\proj", wins) == 2


def test_separators_and_case_do_not_matter():
    wins = [(7, "x [c:/USERS/yyc/IdeaProjects/Thing]")]
    assert J.pick_window(r"C:\Users\YYC\ideaprojects\thing", wins) == 7


def test_trailing_separator_on_cwd_is_tolerated():
    assert J.pick_window("C:/x/proj/", [(9, "proj – a.java")]) == 9


def test_dash_variants_split_the_title():
    for title in ("proj – a.java", "proj — a.java", "proj - a.java", "proj [x]"):
        assert J.pick_window(r"C:\x\proj", [(3, title)]) == 3, title


def test_plain_hyphen_inside_a_name_is_not_a_separator():
    # "a-b" must stay one segment; only a spaced dash separates title parts
    assert J.pick_window(r"C:\x\a-b", [(4, "a-b")]) == 4


def test_project_name_is_the_last_path_segment():
    assert J.project_name(r"C:\Users\YYC\IdeaProjects\bnk-approval-fe") == "bnk-approval-fe"
    assert J.project_name("C:/x/proj/") == "proj"
    assert J.project_name(None) is None
    assert J.project_name("") is None


def test_focus_activates_the_matched_window():
    activated = []
    hwnd = J.focus(r"C:\x\proj", lambda: [(5, "proj – a.java")], activated.append)
    assert hwnd == 5 and activated == [5]


def test_focus_does_nothing_when_no_window_matches():
    activated = []
    assert J.focus(r"C:\x\nope", lambda: [(5, "proj – a.java")], activated.append) is None
    assert activated == []


def test_focus_survives_a_failing_enumerator():
    def boom():
        raise OSError("enumeration failed")

    assert J.focus(r"C:\x\proj", boom, lambda _h: None) is None


def _transcript(tmp_path, session_id, lines):
    d = tmp_path / "C--Users-YYC-IdeaProjects-thing"
    d.mkdir()
    (d / (session_id + ".jsonl")).write_text("\n".join(lines), encoding="utf-8")
    return str(tmp_path)


def test_cwd_from_transcript_finds_a_later_cwd_line(tmp_path):
    # the first lines of a real transcript carry no cwd, and one may not parse
    base = _transcript(tmp_path, "sess1", [
        '{"type": "summary", "leafUuid": "x"}',
        'not json at all',
        json.dumps({"type": "user", "cwd": r"C:\Users\YYC\IdeaProjects\thing"}),
    ])
    assert J.cwd_from_transcript("sess1", base) == r"C:\Users\YYC\IdeaProjects\thing"


def test_cwd_from_transcript_without_a_cwd_field(tmp_path):
    base = _transcript(tmp_path, "sess2", ['{"type": "summary"}'])
    assert J.cwd_from_transcript("sess2", base) is None


def test_cwd_from_transcript_for_an_unknown_session(tmp_path):
    base = _transcript(tmp_path, "sess3", ['{"cwd": "C:/x"}'])
    assert J.cwd_from_transcript("other", base) is None
    assert J.cwd_from_transcript(None, base) is None


def test_cwd_from_transcript_stops_before_reading_a_whole_transcript(tmp_path):
    # a long session's transcript is megabytes; the scan must give up early
    base = _transcript(tmp_path, "sess4", ['{"type": "summary"}'])
    served = []

    def reader(_path):
        for i in range(100000):
            served.append(i)
            yield '{"type": "assistant"}'

    assert J.cwd_from_transcript("sess4", base, reader) is None
    assert len(served) < 1000, len(served)
