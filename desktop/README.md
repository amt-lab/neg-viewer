# Neg Viewer (desktop)

Python / PyQt6 version of the viewer, for a Mac with a USB HDMI capture dongle: camera or capture card → `process_image()` (NumPy) → window. The browser version is `../index.html`.

Tested in demo mode and with the Mac's built-in camera, not yet with a capture dongle.

## Setup

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`opencv-python-headless` is used on purpose: the full `opencv-python` bundles its own Qt, which can conflict with PyQt6.

## Run

```sh
python3 neg_viewer.py --demo        # fake negative, no hardware
python3 neg_viewer.py --list        # find the capture dongle's index
python3 neg_viewer.py --camera 1
```

With the capture dongle:

1. Set the camera's HDMI output to "clean" (no on-screen info) and stop it going to sleep.
2. Connect camera → HDMI → dongle → Mac.
3. Check the hardware in QuickTime Player: File → New Movie Recording, and choose the dongle next to the record button.
4. Run `--list`, then `--camera N`. The built-in camera is usually 0.
5. If the camera cannot be opened: System Settings → Privacy & Security → Camera, enable your terminal app, and restart it.

## Options

| Option | Default | |
|---|---|---|
| `--camera N` | 0 | OpenCV camera index (see `--list`) |
| `--width`, `--height` | 1920, 1080 | Capture resolution to request |
| `--demo` | | Fake negative, no hardware needed |
| `--video FILE` | | Play a video file in a loop instead of a camera |
| `--list` | | List cameras and exit |
| `--max-fps` | 30 | Display refresh cap. 10–15 is plenty; lower it if processing gets heavy |
| `--process-width` | 960 | Downscale to this width before processing. `0` = full resolution |
| `--save-dir` | `~/Pictures/neg-viewer` | Where Save writes PNGs |

The status bar shows source fps · displayed fps · processing time · processing size. Old frames are dropped, so the picture never lags.

## Controls

| Control | Key | |
|---|---|---|
| Drag on image | | Set the metering rectangle |
| Click image | Esc | Clear it (meter the full frame) |
| Invert, B&W, Lock levels | I, M, L | Lock levels stops re-metering |
| Freeze | Space | Hold the current frame; sliders and metering still apply |
| Orig | O (hold) | Show the feed without processing |
| Rotate, Flip H, Flip V | R, H, V | Clears the metering rectangle |
| Clip slider | | % of pixels clipped at each end, per channel |
| Gamma slider | | Midtone brightness |
| Save | S | Full-resolution PNG to `--save-dir` |
| Full screen, Hide controls | F, P | |

## Code

**`processing.py`** (no Qt)

- `process_image(x, settings, lo, hi)` — the function to experiment with. Float32 RGB in [0, 1], shape (H, W, 3), in and out. Normalise each channel → invert → gamma → optional B&W.
- `measure_levels(x, settings)` — per-channel percentile black and white points, from the whole image or the metering rectangle.
- `Settings` — the parameters.
- `NegativeProcessor.process(frame_bgr)` — downscales, converts to float RGB, re-measures levels every 0.1 s on a 160-px copy with light smoothing, calls `process_image()`, returns uint8 RGB.

**`neg_viewer.py`**

- `FrameSource` — background thread that reads the camera, video file or demo and keeps only the newest frame.
- `MainWindow` — a timer at `--max-fps` takes the newest frame, orients, processes and displays it.
- `View` — draws the frame letterboxed and handles dragging the metering rectangle.
