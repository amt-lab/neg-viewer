# Future Steps and Improvements

Ideas for the browser app, roughly in priority order. None are started.

## Constraints to keep

- One self-contained HTML file, no dependencies.
- No accounts, uploads or server-side processing.
- Good defaults; no precise alignment needed in normal use.
- Approximate colour is fine. This is not a scanner.
- Apple devices are the main target; other browsers should degrade gracefully.
- Optional features are capability-detected: if the browser or camera lacks one, hide its control.

## 1. Small improvements

- Remember more settings (orientation, Clip, Gamma, B&W, Invert, panel hidden), with a **Reset settings** command. Never restore Freeze or Lock.
- Clearer messages for permission denied, missing camera, and save or share failure.

## 2. Crop, zoom and framing

- **Display zoom:** a slider that enlarges the centre of the feed, with optional positioning. Done in the shader.
- **Crop to box:** make the metering box fill the display. The crop then applies to display, metering and the saved image together.
- **Frame guides:** overlays for 35 mm, square and 120 formats. Not included in saved images.
- **Whole-strip mode:** keep several frames in view with gentler auto levels, as a quick contact view.

## 3. Capture and save

- **Share sheet on iPhone and iPad** (Web Share), so a frame can go straight to Photos, Files or AirDrop. Fall back to download.
- **Resolution choice:** Automatic / HD / 4K. HD stays the default.
- **Take photo:** try the Image Capture API (`takePhoto()`) for a higher-resolution still where supported, processed with the same settings. Keep the current frame save as the fallback. Of little use with an HDMI capture card.
- Optional filenames with local time, roll name and frame number.

## 4. Camera controls

Shown only when the video track reports the capability. They do not apply to a camera connected through an HDMI capture card.

- Focus: mode, manual distance, focus once and hold.
- Exposure and white balance: manual or locked. This solves what **Lock levels** cannot: the incoming image itself changing.
- Camera zoom, labelled separately from display zoom.
- Lens selection on multi-camera phones: experimental; web pages do not get reliable access.

## 5. App behaviour

- Web-app manifest and icons for **Add to Home Screen**.
- Minimal service worker for offline loading, with a visible version string so updates are not confusing.
- Screen Wake Lock, so the phone does not dim.
- Recover cleanly from interruptions (backgrounding, phone lock, calls, camera unplugged) without reusing stale locked levels.

## 6. Processing

The current percentile stretch stays the default.

- Histogram or clipping overlay.
- Film-base sampling: tap the clear film between frames, then invert by density (`D = -log10(v / base)`), stretch and apply a tone curve.
- Presets as plain collections of settings: colour negative, B&W negative, slide.
- Before/after divider as an alternative to holding **Orig**.

## 7. Session tools

Only if saving becomes part of the selection workflow: thumbnail tray, keeper/reject marks, roll and frame labels, batch export, contact sheet. All local.

## Test matrix

| Platform | Check |
|---|---|
| iPhone Safari | Rear cameras, portrait and landscape, save, permission reset |
| iPhone Home Screen | Relaunch, suspension, safe areas |
| iPad Safari | Built-in and external cameras |
| Mac Safari | Built-in camera, Continuity Camera, HDMI capture card |
| Mac Chrome | Webcam, HDMI capture card |
| Android Chrome | Camera, metering, Freeze, Save |

For each source: reported and saved resolution, rotation and flips, the startup metering box, a custom box, Lock against camera auto-adjustment, Freeze, Save, Orig, and no overlays in the saved image.

## Non-goals

Scan-quality or colour-managed output, cloud uploads, accounts, a processing server, a large framework, mandatory precise alignment.
