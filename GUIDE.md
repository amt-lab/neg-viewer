# Neg Viewer — Guide

For the browser app, `index.html`. Running it and the control list are in [`README.md`](README.md).

## Workflow

1. Put the film on an even, diffuse light source. Keep the camera steady and parallel to the film. Masking the bare light around the film with dark card helps.
2. Open the app and allow camera access. Pick another camera from the menu if needed.
3. Rotate or flip until the frame is the right way round.
4. Place the frame roughly in the centre. The green dashed box is the metering area; the default one is usually fine.
5. Once the picture looks right, turn on **Lock levels**, then move along the strip.
6. **Freeze** to inspect a frame, **Save** to keep it.

Starting points: colour negative — Invert on; B&W negative — Invert and B&W on; slide — Invert off.

## Metering area

The automatic levels are measured only inside the green dashed box.

- At startup the box covers the central 75% of the width and height, so sprocket holes, film edges and the light box are mostly ignored without careful alignment.
- Drag on the image to draw a different box, inside the picture area.
- Tap the image (or press Esc) to remove the box and meter the full frame.
- Reloading the page brings back the startup box.
- The box only affects metering. It does not crop the view or the saved image.
- The box stays at the same place on screen when you rotate or flip, so it may then cover a different part of the film.

To change the startup size, edit `INITIAL_METERING_FRACTION` at the top of the script.

## Lock levels and Freeze

| | Lock levels | Freeze |
|---|---|---|
| Holds the camera frame | No | Yes |
| Stops level measurement | Yes | No |

- While locked, changing the metering box or Clip has no effect until you unlock. Gamma, Invert, B&W and orientation still work.
- While frozen, everything can still be adjusted on the held frame, including the metering box.
- Lock holds the app's levels only. The camera's own auto exposure and white balance can still shift; a web page cannot lock them.
- After switching cameras, unlock briefly so the new feed is measured.

## Other controls

- **Clip:** 0–5%. Higher gives more contrast; lower keeps more highlight and shadow detail. At 0%, one speck or reflection can flatten the whole image.
- **Gamma:** 0.4–2.5. Above 1 brightens the midtones, below 1 darkens them.
- **Invert off** still applies the per-channel levels. Useful for slides.
- **Orig** (hold) skips levels, inversion, gamma and B&W; rotation and flips stay. It is the feed as the camera delivers it, not raw sensor data.

## Saving

Save downloads a PNG named `neg-<UTC timestamp>.png`.

- It contains the current view with all processing and orientation applied, without the controls or the metering box.
- Its size is the camera feed's size, shown in the panel as `Feed 1920×1080 · Save 1920×1080`. A quarter-turn rotation swaps width and height.
- It is a video frame, not a full-resolution still from the sensor. The app asks for 1920×1080; the camera decides what it actually delivers.
- On an iPhone, the file goes to Safari's downloads (Files), not Photos.

## What is remembered

Only the selected camera. Everything else returns to its default on reload. If the remembered camera is missing, the app asks for the rear camera.

## How it works

1. About 10 times a second, a 160-px-wide copy of the frame is measured. For each of R, G and B, the black and white points are the values at the Clip percentiles within the metering area. They are smoothed over time to avoid flicker.
2. A WebGL shader stretches each channel between its points, inverts, applies gamma, then B&W — at full resolution and frame rate.

Everything runs in the browser. No frames leave the device.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Camera API unavailable" | Open the page via `https://` or `http://localhost`, not `file://` or plain `http://` |
| Camera permission denied | Allow the camera for the site in the browser settings, then reload or press **Start camera** |
| Wrong camera or lens | Choose another in the camera menu. On an iPhone, try *Back Camera* if the lens keeps switching at close range |
| "WebGL not available" or blank image | Use a current browser with hardware acceleration enabled |
| Colour or contrast keeps changing | Keep the metering box inside the picture, let it settle, then **Lock levels** |
| Still shifting while locked | The camera is changing its own exposure or white balance; the app cannot prevent that |
| Too harsh, lost detail | Lower Clip (with levels unlocked) |
| Box or Clip change does nothing | Turn **Lock levels** off |
| Full screen does nothing | Not supported by that browser; hide the panel with ☰, or add the page to the Home Screen |
