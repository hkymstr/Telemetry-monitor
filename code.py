import board
import busio
import digitalio
import time

# Hardware Configuration
SPI_CONFIG = {
    'clock': board.GP2,
    'mosi': board.GP3,
    'miso': board.GP4,
    'cs_pin': board.GP5,
    'baudrate': 800000,
    'polarity': 0,
    'phase': 0,
    'bits': 8
}

# ADC Configuration
ADC_CHANNELS = {
    0: 0b00001000,
    1: 0b00010000,
    2: 0b00001000,
    3: 0b00000000
}

class ADCReader:
    def __init__(self, spi_config):
        """Initialize ADC reader with SPI configuration."""
        self.spi = busio.SPI(
            clock=spi_config['clock'],
            MOSI=spi_config['mosi'],
            MISO=spi_config['miso']
        )
        
        # Configure chip select pin
        self.cs = digitalio.DigitalInOut(spi_config['cs_pin'])
        self.cs.direction = digitalio.Direction.OUTPUT
        self.cs.value = True  # Default CS high (disabled)
        
        # Store SPI configuration
        self.spi_config = spi_config

    def read_channel(self, channel):
        """Read value from specified ADC channel."""
        if not 0 <= channel <= 3:
            raise ValueError("Channel must be between 0 and 3")

        # Acquire SPI bus
        while not self.spi.try_lock():
            pass
            
        try:
            # Configure SPI parameters
            self.spi.configure(
                baudrate=self.spi_config['baudrate'],
                polarity=self.spi_config['polarity'],
                phase=self.spi_config['phase'],
                bits=self.spi_config['bits']
            )
            
            # Prepare for reading
            result = bytearray(2)
            channel_select = ADC_CHANNELS[channel]
            
            # Perform SPI transaction
            self.cs.value = False  # Enable ADC
            self.spi.write_readinto(bytearray([channel_select, 0x00]), result)
            self.cs.value = True   # Disable ADC
            
            # Extract and return 8-bit result
            return (result[0] & 0x0F) << 4 | (result[1] >> 4)
            
        finally:
            self.spi.unlock()
            time.sleep(0.01)  # Brief delay between readings

    def read_all_channels(self):
        """Read values from all ADC channels."""
        return [self.read_channel(channel) for channel in range(4)]

def format_reading(channel, value):
    """Format ADC reading for display."""
    return (f"Channel {channel}:, Hex: 0x{value:04X}, Binary: {value:08b}, Decimal: {value}")

def main():
    """Main program loop."""
    adc = ADCReader(SPI_CONFIG)
    
    try:
        while True:
            # Read all channels
            readings = adc.read_all_channels()
            
            # Display readings
            for channel, value in enumerate(readings):
                print(format_reading(channel, value))
            print()  # Blank line for readability
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nProgram terminated by user")

if __name__ == "__main__":
    main()
