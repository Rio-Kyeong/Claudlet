import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication
from claudlet.core import creature as C

_app = QApplication.instance() or QApplication(sys.argv)

EXPECTED = {"thinking", "work_computer", "work_search", "work_web",
            "work_agent", "work_skill", "attention", "idle",
            "celebrate", "sleeping", "error", "angry", "walk", "held", "falling"}


def test_states_present():
    assert EXPECTED.issubset(set(C.STATES)), EXPECTED - set(C.STATES)
    assert "waiting" not in C.STATES   # renamed to sleeping


def test_every_state_renders_without_error():
    img = QImage(C.GRID_W * 6, C.GRID_H * 6, QImage.Format.Format_ARGB32)
    for st in EXPECTED:
        for frame in (0, 7, 50, 100):
            for facing in (1, -1):     # left-facing mirrors the body only
                p = QPainter(img)
                C.draw_creature(p, 0, 0, 6, st, frame, facing=facing)
                p.end()


def test_speech_states_have_lines():
    assert set(C.SPEECH) <= set(C.STATES)
    for st in C.SPEECH:
        assert C.SPEECH[st]


NEW_MOTIONS = {"jump", "wave", "sing", "juggle", "float"}


def test_new_motions_present():
    assert NEW_MOTIONS.issubset(set(C.STATES)), NEW_MOTIONS - set(C.STATES)


def test_default_palette_name_matches_constants():
    named = C.palette_colors("default")
    none_path = C.palette_colors(None)
    assert [c.name() for c in named] == [c.name() for c in none_path]


def test_new_motions_render_without_error():
    img = QImage(C.GRID_W * 6, C.GRID_H * 6, QImage.Format.Format_ARGB32)
    for st in NEW_MOTIONS:
        for frame in (0, 7, 50, 100):
            for facing in (1, -1):
                p = QPainter(img)
                C.draw_creature(p, 0, 0, 6, st, frame, facing=facing)
                p.end()


NEW_LOOKS = {"climbdown", "strain", "leap"}


def test_new_looks_present():
    assert NEW_LOOKS.issubset(set(C.STATES)), NEW_LOOKS - set(C.STATES)


def test_new_looks_render_without_error():
    img = QImage(C.GRID_W * 6, C.GRID_H * 6, QImage.Format.Format_ARGB32)
    for st in NEW_LOOKS:
        for frame in (0, 7, 50, 100):
            for facing in (1, -1):
                p = QPainter(img)
                C.draw_creature(p, 0, 0, 6, st, frame, facing=facing)
                p.end()


def test_speech_language_switch():
    # set_lang flips the bubble text; default is Korean
    C.set_lang("ko")
    assert C.speech("thinking") == "고민중…"
    C.set_lang("en")
    assert C.speech("thinking") == "hmm…"
    assert C.speech("asking") == "yeah?"
    C.set_lang("bogus")          # unknown -> Korean fallback
    assert C.speech("thinking") == "고민중…"
    C.set_lang("ko")             # restore default for other tests


def test_energy_param_renders_all_levels_without_error():
    img = QImage(C.GRID_W * 6, C.GRID_H * 6, QImage.Format.Format_ARGB32)
    for st in ("idle", "walk"):
        for energy in (0.0, 0.5, 1.0):
            for frame in (0, 30, 90):
                p = QPainter(img)
                C.draw_creature(p, 0, 0, 6, st, frame, energy=energy)
                p.end()


def test_energy_defaults_to_full_and_is_keyword():
    import inspect
    sig = inspect.signature(C.draw_creature)
    assert sig.parameters["energy"].default == 1.0


def test_gaze_changes_open_eyes():
    def render(gaze):
        img = QImage(C.GRID_W * 6, C.GRID_H * 6, QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        C.draw_creature(p, 0, 0, 6, "idle", 10, gaze=gaze)
        p.end()
        return bytes(img.constBits().asarray(img.sizeInBytes()))

    assert render((-1.0, -1.0)) != render((1.0, 1.0))


def test_energy_droop_changes_render_and_full_matches_default():
    from PyQt6.QtGui import QImage, QPainter

    def _render(state, frame, **kw):
        img = QImage(C.GRID_W * 6, C.GRID_H * 6, QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        C.draw_creature(p, 0, 0, 6, state, frame, **kw)
        p.end()
        return bytes(img.constBits().asarray(img.sizeInBytes()))

    for state in ("idle", "walk"):
        # a tired creature must render differently from a fresh one at some frame
        assert any(_render(state, f, energy=0.0) != _render(state, f, energy=1.0)
                   for f in (0, 20, 45, 60, 90)), f"{state}: droop had no visible effect"
        # energy=1.0 must be byte-identical to omitting energy (backward compat)
        for f in (0, 20, 45, 60, 90):
            assert _render(state, f, energy=1.0) == _render(state, f), \
                f"{state} frame {f}: energy=1.0 differs from default"


REST_POSES = {"observe", "tic", "settle", "doze"}


def test_rest_poses_present():
    assert REST_POSES.issubset(set(C.STATES)), REST_POSES - set(C.STATES)


def test_rest_poses_render_without_error():
    img = QImage(C.GRID_W * 6, C.GRID_H * 6, QImage.Format.Format_ARGB32)
    for st in REST_POSES:
        for frame in (0, 7, 50, 100):
            for facing in (1, -1):
                p = QPainter(img)
                C.draw_creature(p, 0, 0, 6, st, frame, facing=facing)
                p.end()


def _render_palette(palette):
    img = QImage(C.GRID_W * 6, C.GRID_H * 6, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    C.draw_creature(p, 0, 0, 6, "idle", 0, palette=palette)
    p.end()


def test_palettes_registered():
    assert "shiny_teal" in C.PALETTES and "default" in C.PALETTES


def test_palette_colors_default_matches_constants():
    body, hi, lo, bang = C.palette_colors(None)
    assert (body.name(), bang.name()) == (C.ORANGE.name(), C.BANG.name())


def test_draw_with_named_palette_no_error():
    _render_palette("shiny_teal")


def test_draw_with_unknown_palette_falls_back():
    _render_palette("does_not_exist")     # must not raise


def test_project_palette_is_stable_across_calls():
    # md5, not hash(): a salted str hash would recolour the pet every restart
    a = C.palette_for_project("bnk-approval-fe")
    b = C.palette_for_project("bnk-approval-fe")
    assert a == b and a is not None


def test_project_palette_has_the_four_roles():
    p = C.palette_for_project("some-project")
    assert set(p) == {"body", "hi", "lo", "bang"}
    for v in p.values():
        assert QColor(v).isValid(), v


def test_project_palette_separates_projects_open_together():
    names = ["bnk-approval-fe", "bnk-approval-be", "serafin_v2_be", "claudlet"]
    bodies = {C.palette_for_project(n)["body"] for n in names}
    assert len(bodies) == len(names), bodies


def test_project_palette_without_a_project():
    assert C.palette_for_project(None) is None
    assert C.palette_for_project("") is None


def test_palette_from_body_builds_shades_around_the_given_colour():
    p = C.palette_from_body("#2FA88C")
    assert p["body"] == "#2FA88C"
    assert QColor(p["hi"]).lightness() > QColor(p["body"]).lightness()
    assert QColor(p["lo"]).lightness() < QColor(p["body"]).lightness()


def test_palette_from_body_rejects_nonsense():
    assert C.palette_from_body("nonsense") is None
    assert C.palette_from_body("") is None


def test_draw_with_a_project_palette_dict_no_error():
    _render_palette(C.palette_for_project("bnk-approval-fe"))
