# ============================================================================
# LORA HANDLER
# ============================================================================

import time
from typing import Optional

try:
    import board
    import busio
    import digitalio
    import adafruit_rfm9x
    RPI_AVAILABLE = True
except ImportError:
    print("Adafruit CircuitPython RFM9x not available (expected on non-RPi systems)")
    RPI_AVAILABLE = False
    # Define dummy classes for non-RPi systems
    class DummyBoard:
        pass
    class DummyBusio:
        pass
    class DummyDigitalio:
        pass
    class DummyRFM9x:
        pass
    board = DummyBoard()
    busio = DummyBusio()
    digitalio = DummyDigitalio()
    adafruit_rfm9x = DummyRFM9x()

from .config import LORA_CS_PIN, LORA_RST_PIN, LORA_DIO0_PIN, LORA_FREQ
from .logger import logger

class LoRaHandler:
    def __init__(self):
        self.initialized = False
        self.last_rssi = 0
        self.last_snr = 0

        if not RPI_AVAILABLE:
            print("LoRa not available on this platform")
            return

        # Setup pins
        try:
            self.cs = digitalio.DigitalInOut(getattr(board, f'D{LORA_CS_PIN}'))
            self.rst = digitalio.DigitalInOut(getattr(board, f'D{LORA_RST_PIN}'))
            self.dio0 = digitalio.DigitalInOut(getattr(board, f'D{LORA_DIO0_PIN}'))

            spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
            self.rfm9x = adafruit_rfm9x.RFM9x(spi, self.cs, self.rst, LORA_FREQ, baudrate=9600)

            self.rfm9x.sync_word = 0x12
            self.rfm9x.enable_crc = True
            self.rfm9x.spreading_factor = 7
            self.rfm9x.signal_bandwidth = 125000
            self.rfm9x.tx_power = 23
            self.initialized = True

            logger.info("LoRa initialized successfully")
        except Exception as e:
            logger.error(f"LoRa initialization failed: {e}")
            self.initialized = False

    def send(self, data: str) -> bool:
        """Gửi dữ liệu qua LoRa"""
        if not self.initialized:
            logger.warning("LoRa not initialized, cannot send")
            return False
        try:
            self.rfm9x.send(bytes(data, 'utf-8'))
            logger.debug(f"LoRa TX: {data}")
            return True
        except Exception as e:
            logger.error(f"LoRa send failed: {e}")
            return False

    def receive(self, timeout=0.1) -> Optional[str]:
        """Nhận dữ liệu từ LoRa"""
        if not self.initialized:
            return None
        try:
            packet = self.rfm9x.receive(timeout=timeout)
            if packet is not None:
                self.last_rssi = self.rfm9x.last_rssi
                self.last_snr = self.rfm9x.last_snr
                
                try:
                    data = packet.decode('utf-8', errors='ignore').strip()
                    
                    logger.debug(f"LoRa RX (Decoded): {data} (RSSI: {self.last_rssi}, SNR: {self.last_snr})")
                    return data
                except Exception as decode_err:
                    logger.warning(f"Failed to decode packet: {packet}, error: {decode_err}")
                    return None
                    
        except Exception as e:
            logger.warning(f"LoRa receive error: {e}")
        return None

    def reset(self):
        """Reset LoRa module"""
        logger.info("Resetting LoRa module...")
        try:
            if self.initialized:
                self.rfm9x.reset()
                time.sleep(0.5)
                logger.info("LoRa reset successful")
        except Exception as e:
            logger.warning(f"LoRa reset failed: {e}")