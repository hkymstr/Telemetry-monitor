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
CHANNEL_SELECT = [0b0000_0000, 0b0000_1000, 0b0010_0000, 0b0011_0000]


def read_adc(channel):
    while not spi.try_lock():
        pass
    spi.configure(baudrate=800000, polarity=0, phase=0, bits=8)

    """Read a single channel from the ADC."""
    if channel < 0 or channel > 3:
        raise ValueError("Invalid channel. Must be 0-3.")
    # Send the channel selection byte and dummy data
    cs.value = False  # Select the ADC
    result = bytearray(2)
    spi.write_readinto(bytearray([CHANNEL_SELECT[channel], 0x00]), result)
    cs.value = True  # Deselect the ADC

    # Combine the two bytes to form an 8-bit result
    adc_value = result[0]  # Only take the most significant 8 bits
    spi.unlock()
    return adc_value

def main():
    """Main loop to retrieve telemetry data every second."""
    while True:
        # Read all four channels and store the results in a tuple
        telemetry = tuple(read_adc(channel) for channel in range(4))
        print("Telemetry Data (Tuple):", telemetry)
        print((telemetry))
        print((random.randint(0, 100), random.randint(-100, 0), random.randint(-50, 50)))
        time.sleep(0.5)

# Initialize SPI and run the main loop
with spi:
    main()  # Write your code here :-)
