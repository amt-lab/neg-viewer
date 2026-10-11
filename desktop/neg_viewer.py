"""Live film-negative viewer: camera / HDMI capture card -> process() -> window.

    python neg_viewer.py --list          # find the capture card's index
    python neg_viewer.py --camera 1      # run
    python neg_viewer.py --demo          # synthetic negative, no hardware needed

Before this, check the capture card works in QuickTime Player (File > New Movie Recording,
pick the device next to the record button).
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QSlider, QToolBar, QWidget

from processing import NegativeProcessor

BACKEND = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY


# ---------------------------------------------------------------- frame sources

class FrameSource(threading.Thread):
    """Reads frames on a background thread and keeps only the newest one.

    The UI always takes the latest frame, so if processing or drawing is slower than
    the camera, frames are dropped instead of piling up as lag.
    """

    def __init__(self, read, pace: float | None = None):
        super().__init__(daemon=True)
        self._read = read          # () -> BGR frame or None
        self._pace = pace          # seconds per frame, for sources that aren't paced by hardware
        self._lock = threading.Lock()
        self._frame = None
        self._seq = 0
        self._running = True

    def run(self):
        while self._running:
            t = time.monotonic()
            frame = self._read()
            if frame is None:
                time.sleep(0.01)
                continue
            with self._lock:
                self._frame, self._seq = frame, self._seq + 1
            if self._pace:
                time.sleep(max(0.0, self._pace - (time.monotonic() - t)))

    def latest(self):
        with self._lock:
            return self._frame, self._seq

    def stop(self):
        self._running = False
        self.join(timeout=1)


def camera_source(index: int, width: int, height: int) -> FrameSource:
    cap = cv2.VideoCapture(index, BACKEND)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        sys.exit(f"Could not open camera {index}. Try --list; on macOS also check camera permission "
                 "for your terminal app (System Settings > Privacy & Security > Camera).")

    def read():
        ok, frame = cap.read()
        return frame if ok else None

    return FrameSource(read)


def video_source(path: str) -> FrameSource:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        sys.exit(f"Could not open video {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    def read():
        ok, frame = cap.read()
        if not ok:  # loop
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        return frame if ok else None

    return FrameSource(read, pace=1 / fps)


def demo_source(width: int = 1280, height: int = 720) -> FrameSource:
    """A fake colour negative (orange mask, inverted tones) with a moving ball, for trying the app."""
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    pos = np.zeros((height, width, 3), np.float32)             # the "positive" scene, BGR 0..1
    pos[:] = (x / width)[..., None]                            # grey ramp
    bands = [(0.2, 0.3, 0.9), (0.2, 0.8, 0.3), (0.9, 0.4, 0.2), (0.3, 0.8, 0.9), (0.8, 0.3, 0.8)]
    for i, c in enumerate(bands):                              # colour patches along the bottom
        pos[int(height * .7):int(height * .9), int(width * (.1 + .16 * i)):int(width * (.22 + .16 * i))] = c

    def to_negative(p):
        density = 0.25 + 1.6 * np.asarray(p, np.float32)       # dense where the scene is bright
        trans = 10 ** -density * np.float32([0.35, 0.6, 0.95])  # orange mask: blue cut most, red least
        return np.clip((trans / 0.6) ** (1 / 2.2) * 255, 0, 255).astype(np.uint8)

    background = to_negative(pos)
    ball = tuple(int(v) for v in to_negative([[[0.95, 0.9, 0.3]]])[0, 0])
    t0 = time.monotonic()

    def read():
        t = time.monotonic() - t0
        frame = background.copy()
        cx = int(width * (0.5 + 0.3 * np.sin(t)))
        cv2.circle(frame, (cx, int(height * 0.35)), height // 8, ball, -1, cv2.LINE_AA)
        return frame

    return FrameSource(read, pace=1 / 30)


def list_cameras():
    try:
        from PyQt6.QtMultimedia import QMediaDevices
        app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841 (QMediaDevices needs an app)
        names = [d.description() for d in QMediaDevices.videoInputs()]
        print("Cameras macOS reports (the index order usually matches, but not guaranteed):")
        for i, n in enumerate(names):
            print(f"  {i}: {n}")
    except ImportError:
        pass
    print("Probing OpenCV indices:")
    for i in range(6):
        cap = cv2.VideoCapture(i, BACKEND)
        if cap.isOpened():
            ok, frame = cap.read()
            size = f"{frame.shape[1]}x{frame.shape[0]}" if ok else "opened, but no frame"
            print(f"  --camera {i}: {size}")
        cap.release()


# ---------------------------------------------------------------- display

class View(QWidget):
    """Draws the latest frame letterboxed, and lets you drag a metering rectangle on it."""

    def __init__(self, on_roi):
        super().__init__()
        self.on_roi = on_roi       # callback(roi or None), roi = (x0, y0, x1, y1) in 0..1
        self.roi = None
        self._pix: QPixmap | None = None
        self._drag: QPointF | None = None
        self.setMinimumSize(320, 180)

    def target_size(self) -> tuple[int, int]:
        """Size in physical pixels (Retina aware), so frames can be resized once, with OpenCV."""
        dpr = self.devicePixelRatioF()
        return max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr))

    def show_frame(self, rgb: np.ndarray):
        tw, th = self.target_size()
        h, w = rgb.shape[:2]
        scale = min(tw / w, th / h)
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
        rgb = np.ascontiguousarray(cv2.resize(rgb, size, interpolation=interp))
        img = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888)
        self._pix = QPixmap.fromImage(img)  # copies the data, so rgb can go away
        self._pix.setDevicePixelRatio(self.devicePixelRatioF())
        self.update()

    def image_rect(self) -> QRectF:
        if not self._pix:
            return QRectF()
        size = self._pix.deviceIndependentSize()
        return QRectF((self.width() - size.width()) / 2, (self.height() - size.height()) / 2,
                      size.width(), size.height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.GlobalColor.black)
        if not self._pix:
            return
        r = self.image_rect()
        p.drawPixmap(r.topLeft(), self._pix)
        if self.roi:
            x0, y0, x1, y1 = self.roi
            p.setPen(QPen(QColor(0, 255, 0), 1, Qt.PenStyle.DashLine))
            p.drawRect(QRectF(r.x() + x0 * r.width(), r.y() + y0 * r.height(),
                              (x1 - x0) * r.width(), (y1 - y0) * r.height()))

    def _norm(self, pos: QPointF) -> QPointF:
        r = self.image_rect()
        if r.isEmpty():
            return QPointF()
        return QPointF(min(1, max(0, (pos.x() - r.x()) / r.width())),
                       min(1, max(0, (pos.y() - r.y()) / r.height())))

    def mousePressEvent(self, e):
        self._drag = self._norm(e.position())

    def mouseMoveEvent(self, e):
        if self._drag is None:
            return
        a, b = self._drag, self._norm(e.position())
        if abs(a.x() - b.x()) > 0.02 or abs(a.y() - b.y()) > 0.02:
            self.roi = (min(a.x(), b.x()), min(a.y(), b.y()), max(a.x(), b.x()), max(a.y(), b.y()))
            self.on_roi(self.roi)
            self.update()

    def mouseReleaseEvent(self, e):
        a, b = self._drag, self._norm(e.position())
        self._drag = None
        if a is not None and abs(a.x() - b.x()) <= 0.02 and abs(a.y() - b.y()) <= 0.02:
            self.clear_roi()  # a click without dragging resets to full-frame metering

    def clear_roi(self):
        self.roi = None
        self.on_roi(None)
        self.update()


# ---------------------------------------------------------------- main window

class MainWindow(QMainWindow):
    def __init__(self, source: FrameSource, save_dir: Path, max_fps: float, process_width: int):
        super().__init__()
        self.setWindowTitle("Neg Viewer")
        self.source = source
        self.save_dir = save_dir
        self.proc = NegativeProcessor()
        self.proc.settings.process_width = process_width
        self.rot = 0                     # quarter turns clockwise
        self.flip_h = self.flip_v = False
        self.frozen: np.ndarray | None = None
        self.show_orig = False
        self.last_out: np.ndarray | None = None     # last displayed image, RGB
        self.last_frame: np.ndarray | None = None   # the oriented source frame it came from, BGR
        self._last_seq = -1
        self._dirty = True               # settings changed: redraw even without a new frame

        self.view = View(self._set_roi)
        self.setCentralWidget(self.view)
        self._build_toolbar()

        self.stats = QLabel()
        self.statusBar().addPermanentWidget(self.stats)
        self._counts = {"shown": 0, "seq": 0, "t": time.monotonic(), "ms": 0.0}

        self.timer = QTimer(self, timeout=self._tick)
        self.timer.start(int(1000 / max_fps))
        stats_timer = QTimer(self, timeout=self._update_stats)
        stats_timer.start(500)

    # ---- toolbar

    def _build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, tb)
        self.toolbar = tb
        s = self.proc.settings

        def toggle(text, key, checked, fn):
            a = QAction(text, self, checkable=True, checked=checked)
            a.setShortcut(QKeySequence(key))
            a.setToolTip(f"{text} ({key})")
            a.toggled.connect(lambda on: (fn(on), self._mark_dirty()))
            tb.addAction(a)
            self.addAction(a)  # keep the shortcut working when the toolbar is hidden
            return a

        def button(text, key, fn):
            a = QAction(text, self)
            a.setShortcut(QKeySequence(key))
            a.setToolTip(f"{text} ({key})")
            a.triggered.connect(lambda: (fn(), self._mark_dirty()))
            tb.addAction(a)
            self.addAction(a)  # keep the shortcut working when the toolbar is hidden

        toggle("Invert", "I", s.invert, lambda on: setattr(s, "invert", on))
        toggle("B&&W", "M", s.mono, lambda on: setattr(s, "mono", on))
        toggle("Lock levels", "L", s.lock, lambda on: setattr(s, "lock", on))
        self.freeze_action = toggle("Freeze", "Space", False, self._set_freeze)

        orig = QPushButton("Orig")
        orig.setToolTip("Hold to see the raw feed (O)")
        orig.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        orig.pressed.connect(lambda: self._set_orig(True))
        orig.released.connect(lambda: self._set_orig(False))
        tb.addWidget(orig)

        tb.addSeparator()
        # The ROI is in display coordinates, so it no longer covers the same film after a re-orientation.
        button("Rotate", "R", lambda: (setattr(self, "rot", (self.rot + 1) % 4), self.view.clear_roi()))
        toggle("Flip H", "H", False, lambda on: (setattr(self, "flip_h", on), self.view.clear_roi()))
        toggle("Flip V", "V", False, lambda on: (setattr(self, "flip_v", on), self.view.clear_roi()))
        tb.addSeparator()

        self._slider(tb, "Clip", 0, 50, s.clip_pct * 10, lambda v: setattr(s, "clip_pct", v / 10), "{:.1f}%", 10)
        self._slider(tb, "Gamma", 40, 250, s.gamma * 100, lambda v: setattr(s, "gamma", v / 100), "{:.2f}", 100)
        tb.addSeparator()

        button("Save", "S", self._save)
        button("Full screen", "F", self._toggle_fullscreen)
        button("Hide controls", "P", lambda: tb.setVisible(not tb.isVisible()))
        button("Clear ROI", "Escape", self.view.clear_roi)

    def _slider(self, tb, name, lo, hi, value, fn, fmt, div):
        label = QLabel()
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(lo, hi)
        sl.setFixedWidth(110)
        sl.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        def changed(v):
            fn(v)
            label.setText(f" {name} {fmt.format(v / div)} ")
            self._mark_dirty()

        sl.valueChanged.connect(changed)
        sl.setValue(int(round(value)))
        changed(sl.value())
        tb.addWidget(label)
        tb.addWidget(sl)

    # ---- state changes

    def _mark_dirty(self):
        self._dirty = True

    def _set_roi(self, roi):
        self.proc.settings.roi = roi
        self._mark_dirty()

    def _set_freeze(self, on):
        frame, _ = self.source.latest()
        self.frozen = frame.copy() if on and frame is not None else None

    def _set_orig(self, on):
        self.show_orig = on
        self._mark_dirty()

    def _toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def _save(self):
        """Re-process the source frame at full resolution with the current levels, and save it."""
        if self.last_frame is None:
            return
        rgb = self.last_frame if self.show_orig else self.proc.process(self.last_frame, width=0, meter=False)
        if self.show_orig:
            rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        path = self.save_dir / f"neg-{time.strftime('%Y%m%d-%H%M%S')}.png"
        cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        self.statusBar().showMessage(f"Saved {path}", 4000)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_O and not e.isAutoRepeat():
            self._set_orig(True)
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key.Key_O and not e.isAutoRepeat():
            self._set_orig(False)
        super().keyReleaseEvent(e)

    def resizeEvent(self, e):
        self._mark_dirty()
        super().resizeEvent(e)

    # ---- frame loop

    def _orient(self, frame: np.ndarray) -> np.ndarray:
        if self.flip_h:
            frame = cv2.flip(frame, 1)
        if self.flip_v:
            frame = cv2.flip(frame, 0)
        if self.rot:
            frame = cv2.rotate(frame, [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180,
                                       cv2.ROTATE_90_COUNTERCLOCKWISE][self.rot - 1])
        return frame

    def _tick(self):
        frame, seq = self.source.latest()
        if self.frozen is not None:
            frame = self.frozen          # keep processing it, so sliders and ROI still apply
        elif frame is None or (seq == self._last_seq and not self._dirty):
            return                       # no new frame, nothing changed
        self._last_seq, self._dirty = seq, False

        t0 = time.perf_counter()
        img = self._orient(frame)
        out = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if self.show_orig else self.proc.process(img)
        ms = (time.perf_counter() - t0) * 1000
        self.last_frame, self.last_out = img, out
        self.view.show_frame(out)

        c = self._counts
        c["shown"] += 1
        c["ms"] = ms if c["ms"] == 0 else 0.9 * c["ms"] + 0.1 * ms

    def _update_stats(self):
        c = self._counts
        now = time.monotonic()
        dt = now - c["t"]
        _, seq = self.source.latest()
        cam_fps, shown_fps = (seq - c["seq"]) / dt, c["shown"] / dt
        c.update(shown=0, seq=seq, t=now)
        size = f"{self.last_out.shape[1]}×{self.last_out.shape[0]}" if self.last_out is not None else "-"
        self.stats.setText(f"source {cam_fps:.0f} fps · shown {shown_fps:.0f} fps · "
                           f"process {c['ms']:.1f} ms · {size}")

    def closeEvent(self, e):
        self.timer.stop()
        self.source.stop()
        super().closeEvent(e)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camera", type=int, default=0, help="OpenCV camera index (see --list)")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--video", help="play a video file instead of a camera")
    ap.add_argument("--demo", action="store_true", help="synthetic negative, no hardware needed")
    ap.add_argument("--list", action="store_true", help="list cameras and exit")
    ap.add_argument("--max-fps", type=float, default=30,
                    help="display refresh cap; 10-15 is plenty for viewing, lower it if process() gets heavy")
    ap.add_argument("--process-width", type=int, default=960,
                    help="downscale to this width before process(); 0 = full resolution")
    ap.add_argument("--save-dir", type=Path, default=Path.home() / "Pictures" / "neg-viewer")
    args = ap.parse_args()

    if args.list:
        list_cameras()
        return

    app = QApplication(sys.argv)
    if args.demo:
        source = demo_source()
    elif args.video:
        source = video_source(args.video)
    else:
        source = camera_source(args.camera, args.width, args.height)
    source.start()

    win = MainWindow(source, args.save_dir, args.max_fps, args.process_width)
    win.resize(1280, 800)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
