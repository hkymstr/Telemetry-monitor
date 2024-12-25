import board
import busio
import digitalio
import time
import random
# SPI setup
spi = busio.SPI(clock=board.GP2, MOSI=board.GP3, MISO=board.GP4)  # Define SPI pins
cs = digitalio.DigitalInOut(board.GP5)  # Chip Select pin
cs.direction = digitalio.Direction.OUTPUT
cs.value = True  # Keep CS high when not communicating
# ADC Channel Selection Bits

CHANNEL_SELECT = [0b0000_0000, 0b0000_1000, 0b0001_0000, 0b0001_1000]

# CHANNEL_SELECT = [0b0000_0000, 0b0000_0000, 0b0000_0000, 0b0000_0000]

# CHANNEL_SELECT = [0b0000_1000, 0b0000_1000, 0b0000_1000, 0b0000_1000]

# CHANNEL_SELECT = [0b0001_0000, 0b0001_0000, 0b0001_0000, 0b0001_0000]

# CHANNEL_SELECT = [0b0001_1000, 0b0001_1000, 0b0001_1000, 0b0001_1000]

def read_adc(channel):
    while not spi.try_lock():
        pass
    spi.configure(baudrate=3000000, polarity=0, phase=0, bits=8)
    """Read a single channel from the ADC."""
    if channel < 0 or channel > 3:
        raise ValueError("Invalid channel. Must be 0-3.")
    
    # Send channel selection byte and read the ADC value in two 8-bit transactions
    cs.value = False  # Select the ADC
    result = bytearray(2)  # Buffer for the 16-bit result
    spi.write_readinto(bytearray([CHANNEL_SELECT[channel], 0x00]), result)
    cs.value = True  # Deselect the ADC

    print("channel: ", channel)
    print(result)
    
    # Get the middle 8 bits from the 16-bit result
    adc_value = (result[0] & 0x0F) << 4 | (result[1] >> 4)
    spi.unlock()
    time.sleep(0.5)
    
    return adc_value
    

        
        
def main():
    """Main loop to retrieve telemetry data every second."""
    while True:
        # Read each channel individually and store the results in a list
        telemetry = []
        for channel in range(4):
            value = read_adc(channel)
            telemetry.append(value)
            
            # Print the value for the current channel in hex and binary
            hex_value = f"0x{value:04X}"  # Format the value as a 4-digit hexadecimal
            bin_value = f"{value:08b}"  # Format the value as an 8-bit binary
            print(f"Channel {channel}: Hex: {hex_value}, Binary: {bin_value}")
        
        print(f"Telemetry: {telemetry}")  # Print the complete telemetry list
        print()  # Print a blank line for readability
        
        time.sleep(0.5)
        
        
# Initialize SPI and run the main loop
with spi:
    main()  # Write your code here :-)
