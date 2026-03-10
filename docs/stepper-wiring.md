# Stepper Motor Wiring — Horizontal Pan

## Components
- **Motor:** 28BYJ-48 (5V unipolar stepper)
- **Driver:** ULN2003AN driver board
- **Controller:** Pi Zero W 2

## GPIO Pin Assignment (BCM)

| ULN2003 Input | BCM Pin | Physical Pin | Wire Color (typical) |
|---------------|---------|--------------|----------------------|
| IN1           | 17      | 11           | Blue                 |
| IN2           | 18      | 12           | Pink                 |
| IN3           | 22      | 15           | Yellow               |
| IN4           | 23      | 16           | Orange               |

These pins are all free — no conflicts with the display GPIOs.

## Power

| Connection       | Source                |
|------------------|-----------------------|
| ULN2003 VCC (+)  | 5V pin (physical 2/4) |
| ULN2003 GND (-)  | GND pin (physical 6)  |

**Important:** Power the ULN2003 from the Pi's 5V rail, NOT from 3.3V. The 28BYJ-48 needs 5V. If the Pi's 5V rail can't supply enough current (the motor draws ~240mA), use an external 5V supply with a shared ground.

## Physical Wiring

```
Pi Zero W 2                ULN2003AN Board
─────────────              ───────────────
GPIO 17 (pin 11)  ───────  IN1
GPIO 18 (pin 12)  ───────  IN2
GPIO 22 (pin 15)  ───────  IN3
GPIO 23 (pin 16)  ───────  IN4
5V      (pin 2)   ───────  VCC (+)
GND     (pin 6)   ───────  GND (-)

ULN2003AN Board            28BYJ-48 Motor
───────────────            ──────────────
White connector   ───────  White connector (keyed, only fits one way)
```

## Pi Zero W 2 Header Reference

```
                    Pin 1 (3.3V)  ●  ● Pin 2  (5V) ◄── ULN2003 VCC
              (SDA) Pin 3         ●  ● Pin 4  (5V)
              (SCL) Pin 5         ●  ● Pin 6  (GND) ◄── ULN2003 GND
                    Pin 7         ●  ● Pin 8
                    Pin 9  (GND)  ●  ● Pin 10
  ULN2003 IN1 ──►  Pin 11 (GP17) ●  ● Pin 12 (GP18) ◄── ULN2003 IN2
                    Pin 13        ●  ● Pin 14
  ULN2003 IN3 ──►  Pin 15 (GP22) ●  ● Pin 16 (GP23) ◄── ULN2003 IN4
                    Pin 17 (3.3V) ●  ● Pin 18
                    Pin 19 (MOSI) ●  ● Pin 20 (GND)
                    Pin 21 (MISO) ●  ● Pin 22
                    Pin 23 (SCLK) ●  ● Pin 24 (CE0)
                    Pin 25 (GND)  ●  ● Pin 26 (CE1)
                    ...
```

## Motor Specs (28BYJ-48)
- Voltage: 5V DC
- Step angle: 5.625° / 64 (gear ratio 1:64)
- Steps per revolution: 4096 (half-step) / 2048 (full-step)
- Max speed: ~15 RPM
- Current draw: ~240mA

## Notes
- Use **half-stepping** for smoother movement (4096 steps/rev)
- The step sequence for half-stepping: IN1→IN1+IN2→IN2→IN2+IN3→IN3→IN3+IN4→IN4→IN4+IN1
- De-energize coils when idle to save power and reduce heat
- Mount motor so its shaft drives horizontal (pan/yaw) rotation of the head
- Consider adding a limit switch or soft endstops to prevent over-rotation
