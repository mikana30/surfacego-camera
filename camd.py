#!/usr/bin/env python3
"""Virtual webcam daemon for /dev/video20.
Permanent feeder pipeline (black when idle) + on-demand camera pipeline,
both in one process so the intervideo channel connects them.
The feeder is PAUSED while nobody reads: v4l2sink stays attached (device
remains capture-visible) but stops pushing frames, so idle CPU is ~0."""
import os, subprocess, signal
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

DEV = '/dev/video20'
CAM = '\\\\_SB_.PCI0.LNK1'
IDLE_LIMIT = 6

Gst.init(None)
feeder = Gst.parse_launch(
    'intervideosrc channel=cam ! video/x-raw,format=I420,width=1280,height=720,framerate=15/1 '
    '! videoconvert ! video/x-raw,format=YUY2 ! v4l2sink device=%s sync=true' % DEV)
feeder.set_state(Gst.State.PLAYING)

campipe = None
idle = 0
feeder_paused = False
mypid = str(os.getpid())

def external_readers():
    try:
        out = subprocess.run(['fuser', DEV], capture_output=True, text=True, timeout=5)
        pids = (out.stdout + out.stderr).replace(DEV + ':', '').split()
        return [p for p in pids if p.strip('crem') != mypid and p.strip('crem')]
    except Exception:
        return []

def tick():
    global campipe, idle, feeder_paused
    ext = external_readers()
    if ext:
        idle = 0
        if feeder_paused:
            feeder.set_state(Gst.State.PLAYING)
            feeder_paused = False
            print('FEEDER RESUME', flush=True)
        if campipe is None:
            campipe = Gst.parse_launch(
                'libcamerasrc camera-name="%s" ! video/x-raw,width=1280,height=720,format=NV12 '
                '! videoconvert ! video/x-raw,format=I420 ! videoflip method=counterclockwise ! aspectratiocrop aspect-ratio=16/9 ! videoscale ! videorate ! video/x-raw,format=I420,width=1280,height=720,framerate=15/1,pixel-aspect-ratio=1/1 ! intervideosink channel=cam sync=false' % CAM)
            campipe.get_bus().add_watch(0, lambda b,m,d=None: True, None)
            r = campipe.set_state(Gst.State.PLAYING)
            print('CAM START:', r, flush=True)
    elif campipe is not None:
        idle += 1
        if idle >= IDLE_LIMIT:
            campipe.set_state(Gst.State.NULL)
            campipe = None
            print('CAM STOP', flush=True)
            idle = 0
    elif not feeder_paused:
        idle += 1
        if idle >= IDLE_LIMIT:
            feeder.set_state(Gst.State.PAUSED)
            feeder_paused = True
            print('FEEDER PAUSE', flush=True)
            idle = 0
    return True

GLib.timeout_add_seconds(1, tick)
loop = GLib.MainLoop()
signal.signal(signal.SIGTERM, lambda *a: loop.quit())
loop.run()
feeder.set_state(Gst.State.NULL)
if campipe: campipe.set_state(Gst.State.NULL)
