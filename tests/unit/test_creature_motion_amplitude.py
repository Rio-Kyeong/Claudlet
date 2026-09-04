import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication
from claudlet.core import creature as C

_app = QApplication.instance() or QApplication(sys.argv)

U = 5                                    # the pet's real art-pixel size (pet.py)
W = (C.GRID_W + 2) * U
H = (C.GRID_H + 8) * U


def _rows(state, frame):
    """(top, bottom) device-pixel rows of the drawn creature."""
    img = QImage(W, H, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    C.draw_creature(p, U, 4 * U, U, state, frame)
    p.end()
    buf = bytes(img.constBits().asarray(img.sizeInBytes()))
    rows = [y for y in range(H)
            if any(buf[(y * W + x) * 4 + 3] > 128 for x in range(W))]
    return rows[0], rows[-1]


def _travel(state, frames=range(0, 120)):
    """How far the creature's feet move over a full cycle, in device px.

    The feet, not the top: props (speech bubbles, z's, notes) sit above the head
    and several of them are static, which would mask a body that never moves.
    """
    bottoms = [_rows(state, f)[1] for f in frames]
    return max(bottoms) - min(bottoms)


# Every state below is one the pet holds for minutes at a time while Claude Code
# works. _snap_offset quantises the body offset to whole device pixels, so an
# amplitude under ~0.6 art px (3px at U=5) survives as a 1px twitch or nothing.
MIN_TRAVEL = 3

SUSTAINED = ["work_computer", "work_web", "work_agent", "work_skill",
             "thinking", "asking", "sleeping"]
MOTIONS = ["wave", "sing", "juggle", "error"]


def test_sustained_states_visibly_move():
    for state in SUSTAINED:
        assert _travel(state) >= MIN_TRAVEL, \
            "%s moves only %dpx" % (state, _travel(state))


def test_triggered_motions_visibly_move():
    for state in MOTIONS:
        assert _travel(state) >= MIN_TRAVEL, \
            "%s moves only %dpx" % (state, _travel(state))


def test_error_is_animated_not_a_frozen_pose():
    # it used to set tilt/bob as constants: after frame 0 the body never moved
    assert len({_rows("error", f) for f in range(0, 20)}) > 1
