# Write your code here :-)
# from adafruit_bus_device
# import spi_device
import board
import digitalio

import time
import busio

spi = busio.SPI(board.GP2, MISO=board.GP4, MOSI=board.GP3)
cs = digitalio.DigitalInOut(board.GP5)  # SPI0 CSn is on GP5 (pin 7)
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
cs.direction = digitalio.Direction.OUTPUT


# from adafruit_bus_device.spi_device import SPIDevice
# device = SPIDevice(spi, cs, baudrate=800000, polarity=0, phase=0)

# spi = busio.SPI(board.GP2, MISO=board.GP4, MOSI=board.GP3)
# SPI SCK is on GP2 (pin 4), MISO is GP4, MOSI is GP3

# spi.configure(baudrate=800000, polarity=0, phase=0, bits=8)

# while True:
#    led.value = True
#    cs.value = True
#    print("Led ON")
#    time.sleep(1)
#    led.value = False
#    cs.value = False
#    print("Led OFF")
#    time.sleep(0.5)

cs.value = True

while not spi.try_lock():
    pass
spi.configure(baudrate=800000, polarity=0, phase=0, bits=8)
cs.value = False
spi.write(b"\x00")  # ADC input 1
result = bytearray(1)
spi.readinto(result)
print("ADC1", result)

time.sleep(0.1)

spi.write(b"\x08")  # ADC input 2
result = bytearray(1)
spi.readinto(result)
print("ADC2", result)

time.sleep(0.1)

spi.write(b"\x10")  # ADC input 3
result = bytearray(1)
spi.readinto(result)
print("ADC3", result)

time.sleep(0.1)

spi.write(b"\x20")  # ADC input 3
result = bytearray(1)
spi.readinto(result)
print("ADC4", result)

cs.value = True


print(result)


# while not spi.try_lock():
#    pass

# spi.configure(baudrate=8000000, polarity:int = 0, phase:int=0, bits:int=8)
# cs.value = False
# results = bytearray(4)