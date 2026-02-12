#!/usr/bin/env bash
set -euo pipefail

echo "=== Robot Head Setup ==="
echo ""

# ---- System packages ----
echo "[1/7] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3-pip \
    python3-venv \
    python3-numpy \
    python3-opencv \
    python3-pil \
    python3-picamera2 \
    python3-spidev \
    python3-rpi-lgpio \
    python3-yaml \
    libatlas-base-dev \
    libopenjp2-7

# ---- Enable SPI ----
echo "[2/7] Configuring boot settings..."
CONFIG="/boot/firmware/config.txt"

if ! grep -q "^dtparam=spi=on" "$CONFIG" 2>/dev/null; then
    echo "dtparam=spi=on" | sudo tee -a "$CONFIG" > /dev/null
    echo "  SPI enabled"
fi

# Ensure KMS overlay for camera
if ! grep -q "^dtoverlay=vc4-kms-v3d" "$CONFIG" 2>/dev/null; then
    echo "dtoverlay=vc4-kms-v3d" | sudo tee -a "$CONFIG" > /dev/null
    echo "  KMS overlay enabled"
fi

# Remove gpu_mem if present (bad for Pi Zero 2)
if grep -q "^gpu_mem=" "$CONFIG" 2>/dev/null; then
    sudo sed -i '/^gpu_mem=/d' "$CONFIG"
    echo "  Removed gpu_mem setting"
fi

# ---- SPI buffer size ----
echo "[3/7] Setting SPI buffer size..."
CMDLINE="/boot/firmware/cmdline.txt"
if ! grep -q "spidev.bufsiz" "$CMDLINE" 2>/dev/null; then
    sudo sed -i 's/$/ spidev.bufsiz=131072/' "$CMDLINE"
    echo "  SPI buffer set to 128KB"
fi

# ---- Install project ----
echo "[4/7] Installing project files..."
sudo mkdir -p /opt/robot-head
sudo cp -r . /opt/robot-head/
sudo chown -R "$(whoami):$(whoami)" /opt/robot-head

# ---- Python venv with system packages ----
echo "[5/7] Setting up Python environment..."
python3 -m venv --system-site-packages /opt/robot-head/venv
/opt/robot-head/venv/bin/pip install -q PyYAML

# ---- Systemd services ----
echo "[6/7] Installing main systemd service..."
sudo cp systemd/robot-head.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable robot-head.service

# ---- WiFi watchdog ----
echo "[7/7] Installing WiFi watchdog..."
sudo chmod +x /opt/robot-head/scripts/wifi_watchdog.sh
sudo cp systemd/robot-wifi-watchdog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable robot-wifi-watchdog.service

echo ""
echo "=== Setup complete ==="
echo ""
echo "  IMPORTANT: Reboot to apply SPI and camera settings!"
echo "    sudo reboot"
echo ""
echo "  After reboot the robot head starts automatically."
echo "  Commands:"
echo "    sudo systemctl status robot-head    # Check status"
echo "    sudo systemctl stop robot-head      # Stop"
echo "    sudo systemctl restart robot-head   # Restart"
echo "    journalctl -u robot-head -f         # View logs"
echo ""
echo "  WiFi watchdog:"
echo "    sudo systemctl status robot-wifi-watchdog   # Check watchdog"
echo "    journalctl -u robot-wifi-watchdog -f        # Watchdog logs"
echo ""
echo "  Manual run (with debug stream):"
echo "    cd /opt/robot-head"
echo "    venv/bin/python3 -m src.main --debug"
echo ""
