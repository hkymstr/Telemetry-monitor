import board
import rp2pio
import adafruit_pioasm
import array
import time
import analogio
import microcontroller
from digitalio import DigitalInOut, Direction

# PIO program for continuous SPI communication
CONTINUOUS_SPI = """
.program continuous_spi
.wrap_target
    set x, 15                    ; Set up counter for 16 bits
    mov isr, null                ; Clear ISR before starting input
bitloop:
    set pins, 0                 ; SCK Low
    out pins, 1    [1]         ; Output MOSI and wait
    set pins, 1                 ; SCK High
    in pins, 1     [1]         ; Sample MISO and wait
    jmp x-- bitloop            ; Loop for all 16 bits
    push                       ; Push ISR to FIFO when done
.wrap
"""

# Internal ADC pins
INT_ADC_PINS = [
    board.A0,  # GPIO26 / ADC0
    board.A1,  # GPIO27 / ADC1
    board.A2,  # GPIO28 / ADC2
    board.A3,  # GPIO29 / ADC3
]

class PIOADCReader:
    def __init__(self, sck_pin, mosi_pin, miso_pin, cs_pin, frequency=800000):
        """Initialize ADC reader with PIO-based SPI and internal ADCs."""
        # External ADC channel configurations
        self.channel_configs = {
            0: 0b00000000,
            1: 0b00001000,
            2: 0b00010000,
            3: 0b00011000
        }
        
        # CS pin setup
        self.cs = DigitalInOut(cs_pin)
        self.cs.direction = Direction.OUTPUT
        self.cs.value = True
        
        # PIO setup
        self.assembled = adafruit_pioasm.assemble(CONTINUOUS_SPI)
        self.sm = rp2pio.StateMachine(
            self.assembled,
            frequency=frequency*2,
            first_set_pin=sck_pin,
            set_pin_count=1,
            first_out_pin=mosi_pin,
            out_pin_count=1,
            first_in_pin=miso_pin,
            in_pin_count=1,
            auto_pull=True,
            pull_threshold=16,
            push_threshold=16,
            out_shift_right=False
        )
        
        # Buffers for SPI communication
        self._tx_buffer = array.array('H', [0])
        self._rx_buffer = array.array('H', [0])
        
        # Initialize internal ADC channels
        self.internal_adcs = []
        for pin in INT_ADC_PINS:
            try:
                adc = analogio.AnalogIn(pin)
                self.internal_adcs.append(adc)
            except Exception as e:
                print(f"Warning: Failed to initialize internal ADC on pin {pin}: {e}")
        
        # Pre-start with Ch1 to get correct pipeline order
        self.cs.value = False
        self._tx_buffer[0] = self.channel_configs[1] << 8
        self.sm.write(self._tx_buffer)
        self.cs.value = True
        time.sleep(0.000001)

    def process_value(self, raw):
        """Process raw ADC value into digital value and voltage."""
        value = (raw >> 4) & 0xFF
        digital_value = sum(((value >> i) & 1) << (7-i) for i in range(8))
        voltage = (digital_value / 255.0) * 3.3
        return digital_value, voltage

    def read_external_channels(self):
        """Read all external ADC channels using PIO-based SPI."""
        results = [(0,0.0)] * 4
        channels = [(1,0), (2,1), (3,2), (0,3)]  # (config_channel, result_channel)
        
        for config_ch, result_ch in channels:
            self.cs.value = False
            next_ch = (config_ch + 1) % 4
            self._tx_buffer[0] = self.channel_configs[next_ch] << 8
            self.sm.write_readinto(self._tx_buffer, self._rx_buffer)
            self.cs.value = True
            time.sleep(0.000001)
            
            results[result_ch] = self.process_value(self._rx_buffer[0])
        
        return results

    def read_internal_channel(self, channel):
        """Read value from internal ADC channel."""
        if not 0 <= channel < len(self.internal_adcs):
            raise ValueError(f"Internal channel must be between 0 and {len(self.internal_adcs)-1}")
        
        return self.internal_adcs[channel].value

    def convert_internal_to_voltage(self, value):
        """Convert internal ADC reading to voltage."""
        return (value / 65535) * 3.3

    def read_temperature(self):
        """Read RP2040 internal temperature sensor."""
        try:
            temp_c = microcontroller.cpu.temperature
            temp_f = (temp_c * 9/5) + 32
            return {"celsius": temp_c, "fahrenheit": temp_f}
        except Exception as e:
            print(f"Error reading temperature: {e}")
            return None

    def read_all_channels(self):
        """Read all channels (external and internal) and temperature."""
        readings = {
            'external': self.read_external_channels(),
            'internal': [],
            'temperature': self.read_temperature()
        }
        
        # Read internal channels
        for channel in range(len(self.internal_adcs)):
            try:
                value = self.read_internal_channel(channel)
                voltage = self.convert_internal_to_voltage(value)
                readings['internal'].append((value, voltage))
            except Exception as e:
                print(f"Error reading internal channel {channel}: {e}")
                readings['internal'].append((None, None))
                
        return readings

def format_reading(channel, value_pair, is_internal=False):
    """Format ADC reading for display."""
    if value_pair[0] is None:
        return f"Channel {channel}: ERROR"
    
    if is_internal:
        raw, voltage = value_pair
        return f"Channel {channel}: Raw: 0x{raw:04X}, Decimal: {raw}, Voltage: {voltage:.3f}V"
    else:
        digital_value, voltage = value_pair
        return f"Channel {channel}: Raw: {digital_value}, Voltage: {voltage:.3f}V"

def format_temperature(temp_data):
    """Format temperature reading for display."""
    if temp_data is None:
        return "Temperature: ERROR"
    return f"CPU Temperature: {temp_data['celsius']:.1f}°C / {temp_data['fahrenheit']:.1f}°F"

def main():
    """Main program loop."""
    adc = PIOADCReader(
        sck_pin=board.GP2,
        mosi_pin=board.GP3,
        miso_pin=board.GP4,
        cs_pin=board.GP5,
        frequency=800000
    )
    
    try:
        while True:
            # Read all channels
            readings = adc.read_all_channels()
            
            # Display external readings
            print("\nExternal ADC Readings (3.3V reference):")
            for channel, value_pair in enumerate(readings['external']):
                print(format_reading(channel, value_pair, False))
            
            # Display internal readings
            print("\nInternal ADC Readings (3.3V reference):")
            for channel, value_pair in enumerate(readings['internal']):
                print(format_reading(channel, value_pair, True))
            
            # Display temperature
            print("\nTemperature Reading:")
            print(format_temperature(readings['temperature']))
                
            print("\n" + "-"*50)  # Separator line
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        # Clean up resources
        for adc in adc.internal_adcs:
            adc.deinit()

if __name__ == "__main__":
    main()
