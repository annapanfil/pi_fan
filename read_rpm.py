#!/usr/bin/python3

import RPi.GPIO as gpio
import time

t0 = time.time()
FAN_SPEED_GPIO	= 26
gpio.setmode(gpio.BCM)				 # Select pin reference
gpio.setup(FAN_SPEED_GPIO, gpio.IN, pull_up_down = gpio.PUD_UP) # Declare fan speed pin as input and activate internal pullup resistor
rotates_in_5_sec = 0

def incrementRotates(channel):
    global rotates_in_5_sec
    rotates_in_5_sec += 1

def calcrpm():
    global rotates_in_5_sec
    rpm = 12 * rotates_in_5_sec /2
    rotates_in_5_sec = 0
    print (rpm)

gpio.add_event_detect(FAN_SPEED_GPIO, gpio.RISING, callback = incrementRotates)


if __name__ == '__main__':
    while True:
        time.sleep(5)
        calcrpm()
