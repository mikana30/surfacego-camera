#!/bin/bash
# Installer: virtual webcam for Surface Go (IPU3) cameras in Chrome.
# Run as your normal user; sudo is used where needed.
set -e
sudo dnf install -y akmod-v4l2loopback v4l2loopback libcamera-gstreamer
sudo akmods --force
sudo cp v4l2loopback.conf /etc/modprobe.d/v4l2loopback.conf
echo v4l2loopback | sudo tee /etc/modules-load.d/v4l2loopback.conf >/dev/null
sudo modprobe -r v4l2loopback 2>/dev/null || true
sudo modprobe v4l2loopback
sudo mkdir -p /etc/opt/chrome/policies/managed
sudo cp messenger-media.json /etc/opt/chrome/policies/managed/
mkdir -p ~/bin ~/.config/systemd/user
cp camd.py ~/bin/camd.py && chmod +x ~/bin/camd.py
sed "s|/home/mike|$HOME|" camwatch.service > ~/.config/systemd/user/camwatch.service
systemctl --user daemon-reload
systemctl --user enable --now camwatch.service
echo "Done. Restart Chrome; it will see a webcam named 'Front Camera'."
