import board
import busio
import digitalio
import time
import analogio
import microcontroller

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

# External ADC Configuration
EXT_ADC_CHANNELS = {
    0: 0b00000000,
    1: 0b00001000,
    2: 0b00010000,
    3: 0b00011000
}

# Internal ADC pins
INT_ADC_PINS = [
    board.A0,  # GPIO26 / ADC0
    board.A1,  # GPIO27 / ADC1
    board.A2,  # GPIO28 / ADC2
    board.A3,  # GPIO29 / ADC3
]

class ADCReader:
    def __init__(self, spi_config):
        """Initialize ADC readers with SPI configuration."""
        # External ADC setup
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
        
        # Initialize internal ADC channels
        self.internal_adcs = []
        for pin in INT_ADC_PINS:
            try:
                adc = analogio.AnalogIn(pin)
                self.internal_adcs.append(adc)
            except Exception as e:
                print(f"Warning: Failed to initialize internal ADC on pin {pin}: {e}")

    def read_external_channel(self, channel):
        """Read value from specified external ADC channel, handling pipelined behavior."""
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
            
            # Start first conversion
            result = bytearray(2)
            channel_select = EXT_ADC_CHANNELS[channel]
            
            # First transaction: Setup channel for next conversion
            self.cs.value = False
            self.spi.write_readinto(bytearray([channel_select, 0x00]), result)
            self.cs.value = True
            
            # Brief delay for conversion
            time.sleep(0.000001)  # 1 microsecond delay
            
            # Second transaction: Read the actual result from the channel
            self.cs.value = False
            self.spi.write_readinto(bytearray([channel_select, 0x00]), result)
            self.cs.value = True
            
            # Extract and return 8-bit result
            return (result[0] & 0x0F) << 4 | (result[1] >> 4)
            
        finally:
            self.spi.unlock()
            time.sleep(0.01)  # Brief delay between readings

    def read_internal_channel(self, channel):
        """Read value from internal ADC channel."""
        if not 0 <= channel < len(self.internal_adcs):
            raise ValueError(f"Internal channel must be between 0 and {len(self.internal_adcs)-1}")
        
        return self.internal_adcs[channel].value

    def read_temperature(self):
        """Read RP2040 internal temperature sensor and return both C and F."""
        try:
            temp_c = microcontroller.cpu.temperature
            temp_f = (temp_c * 9/5) + 32
            return {"celsius": temp_c, "fahrenheit": temp_f}
        except Exception as e:
            print(f"Error reading temperature: {e}")
            return None

    def convert_to_voltage(self, value, is_internal=False):
        """Convert ADC reading to voltage."""
        if is_internal:
            # Internal ADC is 16-bit (0-65535) with 3.3V reference
            return (value / 65535) * 3.3
        else:
            # External ADC is 8-bit (0-255) with 3.3V reference
            return (value / 255) * 3.3

    def read_all_channels(self):
        """Read values from all ADC channels (external and internal) and temperature.
        Handles pipelined behavior of external ADC by performing an extra dummy read
        at the start of the sequence."""
        readings = {
            'external': [],
            'internal': [],
            'temperature': self.read_temperature()
        }
        
        # Read external channels
        for channel in range(4):
            try:
                value = self.read_external_channel(channel)
                readings['external'].append(value)
            except Exception as e:
                print(f"Error reading external channel {channel}: {e}")
                readings['external'].append(None)
        
        # Read internal channels
        for channel in range(len(self.internal_adcs)):
            try:
                value = self.read_internal_channel(channel)
                readings['internal'].append(value)
            except Exception as e:
                print(f"Error reading internal channel {channel}: {e}")
                readings['internal'].append(None)
                
        return readings

def format_reading(channel, value, is_internal=False, adc_reader=None):
    """Format ADC reading for display with voltage conversion."""
    if value is None:
        return f"Channel {channel}: ERROR"
        
    voltage = adc_reader.convert_to_voltage(value, is_internal) if adc_reader else 0
    
    base_str = f"Channel {channel}: Hex: 0x{value:04X}, Binary: {value:08b}, Decimal: {value}"
    voltage_str = f", Voltage: {voltage:.3f}V"
    
    return base_str + voltage_str

def format_temperature(temp_data):
    """Format temperature reading for display in both C and F."""
    if temp_data is None:
        return "Temperature: ERROR"
    return f"CPU Temperature: {temp_data['celsius']:.1f}°C / {temp_data['fahrenheit']:.1f}°F"

def main():
    """Main program loop."""
    adc = ADCReader(SPI_CONFIG)
    
    try:
        while True:
            # Read all channels
            readings = adc.read_all_channels()
            
            # Display external readings
            print("\nExternal ADC Readings (3.3V reference):")
            for channel, value in enumerate(readings['external']):
                print(format_reading(channel, value, False, adc))
            
            # Display internal readings
            print("\nInternal ADC Readings (3.3V reference):")
            for channel, value in enumerate(readings['internal']):
                print(format_reading(channel, value, True, adc))
            
            # Display temperature
            print("\nTemperature Reading:")
            print(format_temperature(readings['temperature']))
                
            print("\n" + "-"*50)  # Separator line
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        # Clean up resources
        for adc in adc.internal_adcs:
            adc.deinit()

if __name__ == "__main__":
    main()
