# Robot Head - Wiring Guide

## Components

- Raspberry Pi Zero W 2
- Pi Camera Module 3
- 2x GC9A01 Round 240x240 SPI LCD

## Left Eye Display (GC9A01 #1)

| Display Pin | Connect to | Pi Pin # | Notes |
|-------------|------------|----------|-------|
| VCC | 3.3V | Pin 1 | Power |
| GND | GND | Pin 6 | Ground |
| SCL (SCLK) | GPIO 11 | Pin 23 | SPI clock (shared) |
| SDA (MOSI) | GPIO 10 | Pin 19 | SPI data (shared) |
| CS | GPIO 8 | Pin 24 | CE0 - left eye select |
| DC | GPIO 25 | Pin 22 | Data/Command |
| RST | GPIO 24 | Pin 18 | Reset |
| BL | GPIO 12 | Pin 32 | Backlight (or tie to 3.3V) |

## Right Eye Display (GC9A01 #2)

| Display Pin | Connect to | Pi Pin # | Notes |
|-------------|------------|----------|-------|
| VCC | 3.3V | Pin 17 | Power (second 3.3V pin) |
| GND | GND | Pin 9 | Ground |
| SCL (SCLK) | GPIO 11 | Pin 23 | SPI clock (shared with left) |
| SDA (MOSI) | GPIO 10 | Pin 19 | SPI data (shared with left) |
| CS | GPIO 7 | Pin 26 | CE1 - right eye select |
| DC | GPIO 16 | Pin 36 | Data/Command |
| RST | GPIO 26 | Pin 37 | Reset |
| BL | GPIO 13 | Pin 33 | Backlight (or tie to 3.3V) |

## Camera Module 3

- Connects via the CSI ribbon cable to the camera port on the Pi Zero W 2
- Lift the plastic tab on the CSI connector, slide the ribbon in (contacts facing the board), press the tab down
- No GPIO pins used

## Pi Zero W 2 Header Reference

```
                   +-----+
              3.3V | 1  2| 5V
    (SDA1) GPIO  2 | 3  4| 5V
    (SCL1) GPIO  3 | 5  6| GND          <-- Left GND
           GPIO  4 | 7  8| GPIO 14 (TXD)
               GND | 9 10| GPIO 15 (RXD)  <-- Right GND
           GPIO 17 |11 12| GPIO 18
           GPIO 27 |13 14| GND
           GPIO 22 |15 16| GPIO 23
              3.3V |17 18| GPIO 24      <-- Right VCC / Left RST
  (MOSI)   GPIO 10 |19 20| GND         <-- Left+Right SDA
  (MISO)   GPIO  9 |21 22| GPIO 25     <-- Left DC
  (SCLK)   GPIO 11 |23 24| GPIO  8     <-- Left+Right SCL / Left CS (CE0)
               GND |25 26| GPIO  7     <-- Right CS (CE1)
           GPIO  0 |27 28| GPIO  1
           GPIO  5 |29 30| GND
           GPIO  6 |31 32| GPIO 12     <-- Left BL
           GPIO 13 |33 34| GND         <-- Right BL
           GPIO 19 |35 36| GPIO 16     <-- Right DC
           GPIO 26 |37 38| GPIO 20     <-- Right RST
               GND |39 40| GPIO 21
                   +-----+
```

## Notes

- Both displays share MOSI and SCLK (4 wires total for SPI data, not 8)
- Each display draws ~20-30mA from 3.3V, well within the Pi's capacity
- If a backlight flickers, tie BL directly to 3.3V instead of using the GPIO pin
- The left display uses CE0 and the right uses CE1 - don't mix them up or the eyes will be swapped

## Reserved Pins (for future use)

| GPIO | Possible Use |
|------|-------------|
| 4, 17, 27, 22 | Servos (pan/tilt head) |
| 18, 19, 20, 21 | I2S audio (speaker via MAX98357A) |
