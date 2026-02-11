# Robot Head - Pi Setup Guide

Quick reference for setting up a fresh Raspberry Pi Zero W 2 from scratch.

## Prerequisites

- Raspberry Pi Zero W 2 with Pi OS (Bookworm, headless)
- SSH enabled, user: `robot`, password: `mrrobot`
- Pi Camera Module 3 connected via CSI ribbon cable
- Network configured (current IP: `192.168.2.131`)

## 1. Enable SPI

Uncomment the SPI line in boot config:

```bash
sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/firmware/config.txt
```

Verify it says `dtparam=spi=on` (no `#`):

```bash
grep dtparam=spi /boot/firmware/config.txt
```

## 2. Set SPI Buffer Size

Add `spidev.bufsiz=131072` to the kernel command line:

```bash
sudo sed -i 's/$/ spidev.bufsiz=131072/' /boot/firmware/cmdline.txt
```

## 3. Install System Packages

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-numpy \
    python3-opencv \
    python3-pil \
    python3-picamera2 --no-install-recommends \
    python3-spidev \
    python3-rpi-lgpio \
    python3-yaml \
    opencv-data \
    libatlas-base-dev \
    libopenjp2-7
```

**Note:** `opencv-data` is a separate package that provides the Haar cascade XML files.
On Bookworm, `cv2.data.haarcascades` doesn't exist -- the cascades live at
`/usr/share/opencv4/haarcascades/`.

## 4. Deploy Project Files

Create the project directory on the Pi:

```bash
sudo mkdir -p /opt/robot-head
sudo chown robot:robot /opt/robot-head
```

From the Windows dev machine, copy the source and assets:

```bash
scp -r src/ robot@192.168.2.131:/opt/robot-head/src/
scp -r assets/eyes/ robot@192.168.2.131:/opt/robot-head/assets/eyes/
scp -r systemd/ robot@192.168.2.131:/opt/robot-head/systemd/
scp config.yaml robot@192.168.2.131:/opt/robot-head/
```

### Updating After Code Changes

To push updates to the Pi and restart:

```bash
# Copy changed files (from Windows)
scp src/eyes/style_manager.py robot@192.168.2.131:~/robot-head/src/eyes/
# Then on the Pi, copy to /opt and restart
ssh robot@192.168.2.131 "sudo cp ~/robot-head/src/eyes/style_manager.py /opt/robot-head/src/eyes/ && sudo systemctl restart robot-head"
```

Or copy directly to /opt (requires sudo):

```bash
ssh robot@192.168.2.131 "sudo systemctl restart robot-head"
```

## 5. Create Python Virtual Environment

```bash
python3 -m venv --system-site-packages /opt/robot-head/venv
/opt/robot-head/venv/bin/pip install PyYAML
```

Uses `--system-site-packages` so numpy, opencv, pillow, picamera2, spidev are
all inherited from the system apt packages (no need to compile from source).

## 6. Add User to Hardware Groups

```bash
sudo usermod -aG spi,i2c,video,gpio robot
```

## 7. Install Systemd Service

```bash
sudo cp /opt/robot-head/systemd/robot-head.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable robot-head.service
```

## 8. Reboot

```bash
sudo reboot
```

After reboot, SPI devices appear at `/dev/spidev0.0` and `/dev/spidev0.1`,
and the service starts automatically.

## Verification

```bash
# SPI devices present
ls /dev/spidev*

# Camera detected
python3 -c "from picamera2 import Picamera2; print(Picamera2.global_camera_info())"

# Service running
sudo systemctl status robot-head

# View logs
journalctl -u robot-head -f

# Debug stream (open in browser)
# http://192.168.2.131:8080
```

## Manual Run (for debugging)

```bash
sudo systemctl stop robot-head
cd /opt/robot-head
venv/bin/python3 -u -m src.main --debug
```

## Eye Styles

The debug web UI at `http://192.168.2.131:8080` includes a style switcher panel. Available styles:

- **Procedural (Red Iris)** — default, drawn with Pillow primitives
- **Sprite styles** — image-based eyes loaded from `assets/eyes/`:
  - `bloodshot.png`, `camera_lens.png`, `cyber_eye.png`, `robotic_eyeball.png`

Sprite images are 350x350 px (240 display + gaze offset padding). To add a new sprite:

1. Place a 350x350 PNG with a black background in `assets/eyes/`
2. Restart the service — it auto-discovers `*.png` files in that directory

API endpoints:
- `GET /api/styles` — list styles with active flag
- `POST /api/styles/active` — switch: `{"id": "sprite_cyber_eye"}`

## Gotchas

- **OpenCV 4.6 on Bookworm**: `cv2.data` attribute doesn't exist. Cascade path is hardcoded to `/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml`
- **RPi.GPIO**: The `python3-rpi-lgpio` package provides a compatibility shim that emulates the `RPi.GPIO` API using `lgpio` underneath. Import as `import RPi.GPIO as GPIO` still works.
- **picamera2**: Must be installed via apt (`python3-picamera2`), not pip. Pip version won't have the libcamera bindings.
- **RAM**: Pi Zero W 2 shows 416MB usable (GPU reserves the rest). The robot head uses ~200MB, leaving plenty of headroom.
- **SPI speed**: 62.5 MHz works reliably. Set in `config.yaml` under `display.spi_speed_hz`.
