#!/usr/bin/python3

import RPi.GPIO as gpio
import time

t0 = time.time()
FAN_SPEED_GPIO	= 26
gpio.setmode(gpio.BCM)				 # Select pin reference
gpio.setup(FAN_SPEED_GPIO, gpio.IN, pull_up_down = gpio.PUD_UP) # Declare fan speed pin as input and activate internal pullup resistor

def calcrpm(channel):
    # interrupt function that should calculate the rpm from tacho signal, but sometimes does not work due to interrupt
    global t0
    t1 = time.time()		# get current time
    try:
        #rpm = (60 / (t1-t0)) # This is the normal formula to calculate rpm
        rpm = (30 / (t1-t0)) # Since there are two flanks per rotation we need to half it
    except ZeroDivisionError: pass
    finally:
        t0 = t1
        print(rpm)

gpio.add_event_detect(FAN_SPEED_GPIO, gpio.RISING, callback = calcrpm)


if __name__ == '__main__':
    while True:
        pass
