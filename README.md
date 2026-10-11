# Neg Viewer

A quick, good-enough live viewer for film negatives. Put the film on a light source, point a camera at it, and see the positive on screen. It is for inspecting negatives before scanning, not for scanning them.

It runs in a browser and uses any camera the browser can see: a phone's own camera, a webcam, or a proper camera connected to a computer through a UVC HDMI capture card.

Live: https://amt-lab.github.io/neg-viewer/

## Serving

`index.html` is the whole app, but it must be served: the camera does not work when the file is opened directly.

- **Phone:** needs an `https://` address. Plain `http://` on the local network will not get camera access.
- **Computer:** `python3 -m http.server 8000`, then open `http://localhost:8000/`.

## Controls

The green dashed box is the metering area: the automatic levels are measured inside it. It starts as the central 75% of the frame.

| Control | Key | What it does |
|---|---|---|
| Drag on image | | Draw a new metering area |
| Tap image | Esc | Remove it and meter the full frame |
| Invert | I | Negative → positive (on by default) |
| B&W | M | Monochrome |
| Lock levels | L | Hold the current levels while you move the film |
| Freeze | Space | Hold the current frame |
| Orig | O (hold) | Show the unprocessed feed |
| Rotate / Flip H / Flip V | R / H / V | Orientation |
| Clip | | Contrast: % of pixels clipped at each end |
| Gamma | | Midtone brightness |
| Save | S | Download the current view as a PNG |
| Full screen | F | |
| ☰ | P | Show or hide the controls |

## Desktop alternative

`desktop/` is a separate Python app that does the same job without a browser, for a Mac with a camera on a UVC HDMI capture card. It is optional and not yet tested with a capture card. See [`desktop/README.md`](desktop/README.md).
