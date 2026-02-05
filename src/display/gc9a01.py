import time
import spidev
import RPi.GPIO as GPIO


# GC9A01 command constants
_SWRESET = 0x01
_SLPOUT = 0x11
_INVON = 0x21
_DISPON = 0x29
_CASET = 0x2A
_RASET = 0x2B
_RAMWR = 0x2C
_MADCTL = 0x36
_COLMOD = 0x3A

# Full init sequence derived from Adafruit/LVGL/TFT_eSPI reference drivers
_INIT_SEQUENCE = [
    (0xEF, []),
    (0xEB, [0x14]),
    (0xFE, []),
    (0xEF, []),
    (0x84, [0x40]),
    (0x85, [0xFF]),
    (0x86, [0xFF]),
    (0x87, [0xFF]),
    (0x88, [0x0A]),
    (0x89, [0x21]),
    (0x8A, [0x00]),
    (0x8B, [0x80]),
    (0x8C, [0x01]),
    (0x8D, [0x01]),
    (0x8E, [0xFF]),
    (0x8F, [0xFF]),
    (0xB6, [0x00, 0x00]),
    (0x36, [0x48]),           # MADCTL: row/col exchange, RGB order
    (0x3A, [0x55]),           # COLMOD: RGB565 (16-bit)
    (0x90, [0x08, 0x08, 0x08, 0x08]),
    (0xBD, [0x06]),
    (0xBC, [0x00]),
    (0xFF, [0x60, 0x01, 0x04]),
    (0xC3, [0x13]),
    (0xC4, [0x13]),
    (0xC9, [0x22]),
    (0xBE, [0x11]),
    (0xE1, [0x10, 0x0E]),
    (0xDF, [0x21, 0x0C, 0x02]),
    (0xF0, [0x45, 0x09, 0x08, 0x08, 0x26, 0x2A]),  # Gamma+
    (0xF1, [0x43, 0x70, 0x72, 0x36, 0x37, 0x6F]),  # Gamma-
    (0xF2, [0x45, 0x09, 0x08, 0x08, 0x26, 0x2A]),  # Gamma+
    (0xF3, [0x43, 0x70, 0x72, 0x36, 0x37, 0x6F]),  # Gamma-
    (0xED, [0x1B, 0x0B]),
    (0xAE, [0x77]),
    (0xCD, [0x63]),
    (0x70, [0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03]),
    (0xE8, [0x34]),
    (0x62, [0x18, 0x0D, 0x71, 0xED, 0x70, 0x70,
            0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70]),
    (0x63, [0x18, 0x11, 0x71, 0xF1, 0x70, 0x70,
            0x18, 0x13, 0x71, 0xF3, 0x70, 0x70]),
    (0x64, [0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07]),
    (0x66, [0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45, 0x10, 0x00, 0x00, 0x00]),
    (0x67, [0x00, 0x3C, 0x00, 0x00, 0x00, 0x01, 0x54, 0x10, 0x32, 0x98]),
    (0x74, [0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00]),
    (0x98, [0x3E, 0x07]),
    (0x35, [0x00]),           # Tearing effect on
    (0x21, []),               # Display inversion on
    (0x11, []),               # Sleep out (needs 120ms delay)
    (0x29, []),               # Display on (needs 20ms delay)
]

# SPI transfer chunk size (spidev limit)
_SPI_CHUNK = 4096


class GC9A01:
    """Low-level driver for a single GC9A01 240x240 round LCD over SPI."""

    WIDTH = 240
    HEIGHT = 240

    def __init__(self, spi_bus: int, spi_device: int,
                 dc_pin: int, rst_pin: int, bl_pin: int | None = None,
                 spi_speed_hz: int = 62_500_000):
        self._spi_bus = spi_bus
        self._spi_device = spi_device
        self._dc = dc_pin
        self._rst = rst_pin
        self._bl = bl_pin
        self._speed = spi_speed_hz
        self._spi = None

    def init_display(self):
        """Set up GPIO, SPI, and run the GC9A01 init sequence."""
        # GPIO setup (BCM mode, may already be set by caller)
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._dc, GPIO.OUT)
        GPIO.setup(self._rst, GPIO.OUT)
        if self._bl is not None:
            GPIO.setup(self._bl, GPIO.OUT)
            GPIO.output(self._bl, GPIO.HIGH)

        # SPI setup
        self._spi = spidev.SpiDev()
        self._spi.open(self._spi_bus, self._spi_device)
        self._spi.max_speed_hz = self._speed
        self._spi.mode = 0b00
        self._spi.no_cs = False

        # Hardware reset
        GPIO.output(self._rst, GPIO.HIGH)
        time.sleep(0.01)
        GPIO.output(self._rst, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(self._rst, GPIO.HIGH)
        time.sleep(0.12)

        # Run init sequence
        for cmd, data in _INIT_SEQUENCE:
            self._write_cmd(cmd)
            if data:
                self._write_data(bytes(data))
            if cmd == 0x11:
                time.sleep(0.12)
            elif cmd == 0x29:
                time.sleep(0.02)

    def send_framebuffer(self, buf: bytes | bytearray):
        """Send a complete 240x240 RGB565 framebuffer (115200 bytes)."""
        # Set address window to full screen
        self._set_window(0, 0, self.WIDTH - 1, self.HEIGHT - 1)
        # RAM write command
        self._write_cmd(_RAMWR)
        # Send pixel data in chunks
        GPIO.output(self._dc, GPIO.HIGH)
        mv = memoryview(buf)
        for i in range(0, len(buf), _SPI_CHUNK):
            self._spi.writebytes2(mv[i:i + _SPI_CHUNK])

    def fill(self, color_rgb565: int):
        """Fill the entire display with a single RGB565 color."""
        hi = (color_rgb565 >> 8) & 0xFF
        lo = color_rgb565 & 0xFF
        buf = bytes([hi, lo]) * (self.WIDTH * self.HEIGHT)
        self.send_framebuffer(buf)

    def set_backlight(self, on: bool):
        """Toggle backlight pin."""
        if self._bl is not None:
            GPIO.output(self._bl, GPIO.HIGH if on else GPIO.LOW)

    def cleanup(self):
        """Turn off backlight and close SPI."""
        if self._bl is not None:
            GPIO.output(self._bl, GPIO.LOW)
        if self._spi is not None:
            self._spi.close()

    def _set_window(self, x0: int, y0: int, x1: int, y1: int):
        """Set the column and row address window."""
        self._write_cmd(_CASET)
        self._write_data(bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self._write_cmd(_RASET)
        self._write_data(bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))

    def _write_cmd(self, cmd: int):
        GPIO.output(self._dc, GPIO.LOW)
        self._spi.writebytes([cmd])

    def _write_data(self, data: bytes):
        GPIO.output(self._dc, GPIO.HIGH)
        self._spi.writebytes2(data)
