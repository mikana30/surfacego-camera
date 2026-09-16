# surfacego-camera

Working camera for **Chrome / Messenger video calls on a Surface Go running Fedora Linux**.

Surface Go cameras are Intel IPU3 sensors that browsers cannot use directly:
Chrome's V4L2 path sees only raw ISP nodes, and its experimental PipeWire
camera support deadlocks in `enumerateDevices()`. This project bridges the
front camera into a `v4l2loopback` virtual webcam that Chrome treats as a
normal USB webcam.

## How it works

- `v4l2loopback` (RPM Fusion akmod) creates `/dev/video20` "Front Camera"
  with `exclusive_caps=1` (required: Chrome skips devices advertising OUTPUT caps).
- `camd.py` (systemd user service `camwatch.service`) runs a **single GStreamer
  process** with two pipelines joined by an `intervideo` channel:
  - a permanent feeder (`intervideosrc → v4l2sink`) that keeps the device
    always streamable — black frames when idle, so apps can open it any time;
  - an on-demand camera pipeline (`libcamerasrc → videoflip → intervideosink`)
    started only while another process is reading the webcam, stopped ~6 s
    after they stop. The physical camera and privacy indicator are **off when idle**.
- `messenger-media.json` is a Chrome enterprise policy pre-authorizing
  camera/mic for messenger.com and facebook.com — needed because Chrome's
  permission prompts fail to render under GNOME/Wayland on this device, and
  hand-editing Preferences is ignored (MAC-protected).

## Hard-won details (read before modifying)

- `intervideo` channels are **per-process**: producer and consumer must live
  in one process, hence the Python daemon instead of two `gst-launch` processes.
- v4l2loopback 0.15 allows only **one writer**; swapping writers mid-stream
  fails with "device busy" — hence the permanent feeder + channel switch.
- Readers get a STREAMON I/O error if no writer is attached — another reason
  the feeder never detaches.
- The camera branch must end in caps with explicit
  `pixel-aspect-ratio=1/1` — after `videoflip`+`aspectratiocrop`+`videoscale`
  the PAR otherwise comes out 405/406 and `intervideosrc` dies "not-negotiated"
  (symptom: black frames).
- The libcamera camera name `\_SB_.PCI0.LNK1` needs one extra escaping level
  per parser: `'\\_...'` in shell, `'\\\\_...'` in a Python string handed to
  `Gst.parse_launch`.
- The front sensor is mounted 90°; `videoflip method=counterclockwise` fixes it.

## Install (Fedora, RPM Fusion enabled)

```
./install.sh
```

Then restart Chrome. First frames after the camera wakes are dark for ~2 s
while auto-exposure settles (the IPU3 sensors run uncalibrated on Linux).

## Files

| file | destination |
|---|---|
| `camd.py` | `~/bin/camd.py` |
| `camwatch.service` | `~/.config/systemd/user/` |
| `v4l2loopback.conf` | `/etc/modprobe.d/` |
| `messenger-media.json` | `/etc/opt/chrome/policies/managed/` |
