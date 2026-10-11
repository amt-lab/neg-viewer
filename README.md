# Neg Viewer

A quick, good-enough live viewer for film negatives: film on a light source, camera pointed at it, positive image on screen. It is for inspecting negatives before scanning, not for scanning them.

Each RGB channel is stretched between its measured black and white points (which removes most of the orange mask), then inverted.

| Path | What |
|---|---|
| `index.html` | Browser app. One self-contained file; works on a computer (webcam or HDMI capture card) and on phones |
| `GUIDE.md` | How to use the browser app |
| `desktop/` | Separate Python / PyQt6 app for a Mac with a USB HDMI capture dongle |
| `FUTURE-STEPS-AND-IMPROVEMENTS.md` | Possible improvements |

## Run the browser app

The camera API needs a secure origin: `https://` or `http://localhost`. Opening the file directly (`file://`) does not work.

**On this computer**

```sh
python3 -m http.server 8000
# open http://localhost:8000/
```

**On a phone:** serve the file over HTTPS (e.g. GitHub Pages) and open the URL. A plain `http://` address on the local network will not get camera access.

## Controls

| Control | Key | What it does |
|---|---|---|
| Drag on image | | Set the metering area |
| Tap image | Esc | Clear the metering area (meter the full frame) |
| Invert | I | Negative → positive (on by default) |
| B&W | M | Monochrome output |
| Lock levels | L | Stop re-metering |
| Freeze | Space | Hold the current frame |
| Orig | O (hold) | Show the feed without processing |
| Rotate / Flip H / Flip V | R / H / V | Orientation |
| Clip | | % of pixels clipped at each end of each channel (default 0.5) |
| Gamma | | Midtone brightness (default 1) |
| Save | S | Download the current view as a PNG |
| Full screen | F | |
| ☰ | P | Show or hide the control panel |

See [`GUIDE.md`](GUIDE.md) for details.
