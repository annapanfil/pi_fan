# Raspberry Pi fan control

Python script to manage fan speed in Raspberry Pi.

It reads temperature of Pi and drives (not tested yet) and potencially everything else.
On this base it determines fan speed, trying to keep temperature on desired level.


## Requirements:
python3

libraries (can be downloaded with pip):

- RPi.GPIO

- os

- signal

- time


## Run (only on Rasbpberry Pi):
`./fan_control.py`

or

`python3 fan_control.py`

## add to autostart

## circuit scheme
---
inspired by: [enwi] – [youtube video]

<!-- links -->
[enwi]: https://www.python.org/downloads/
[youtube video]: https://www.youtube.com/watch?v=iMWV6WpySu0
