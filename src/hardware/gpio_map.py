from dataclasses import dataclass


@dataclass(frozen=True)
class GPIOMap:
    """Central pin definitions. All values are BCM pin numbers."""

    # SPI0 (managed by spidev, listed here for documentation)
    SPI_MOSI: int = 10
    SPI_SCLK: int = 11
    SPI_CE0: int = 8
    SPI_CE1: int = 7

    # Left eye display (on CE0)
    LEFT_DC: int = 25
    LEFT_RST: int = 24
    LEFT_BL: int = 12

    # Right eye display (on CE1)
    RIGHT_DC: int = 16
    RIGHT_RST: int = 26
    RIGHT_BL: int = 13
