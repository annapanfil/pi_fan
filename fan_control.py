#!/usr/bin/python3

import RPi.GPIO as gpio
import os
import signal
import time

class Resource:
	def __init__(self, desired_temp: int):
		self.off_temp = desired_temp	# good temperature – turn off the fan
		self.on_temp = desired_temp + 2 # treshold temperature to turn on the fan
		self.curr_temp = None
		self.last_temp = None
		self.fanStatus = 0  # what does resource want from fan: -1 – decrease speed, 1 – increase, 0 – maintain

	def ordersForFan(self) -> int:
		if self.fanStatus == 0:
			if self.curr_temp > self.on_temp: self.fanStatus = 1	# turn on the fan
		elif self.curr_temp > (self.off_temp+10): self.fanStatus = 1 # increase fan speed
		elif self.curr_temp < self.off_temp: self.fanStatus = 0		# "it's ok for me"
		elif self.curr_temp < self.last_temp: self.fanStatus = -1	# temperature is decreasing – slow down the fan
		print(self)
		return self.fanStatus

	def getTemp() -> int:
		pass

	def __str__(self):
		return "fanStatus: " + str(self.fanStatus) + " curr_temp: " + str(self.curr_temp) + " last_temp: " + str(self.last_temp)

class Disk(Resource):
	def __init__(self, desired_temp: int, name: str):
		super().__init__(desired_temp)
		self.name = name

	def getTemp(self) -> int:
		result = os.popen("sudo smartctl -d sat --all /dev/%s | grep Temperature_Celsius | awk '{print $10}'" % self.name).readline()
		return int(result)

class CPU(Resource):
	def __init__(self, desired_temp: int):
		super().__init__(desired_temp)

	def getTemp(self) -> int:
		f = open("/sys/class/thermal/thermal_zone0/temp")
		CPUTemp = f.read()
		f.close()
		self.last_temp = self.curr_temp
		self.curr_temp = int(CPUTemp.replace("\n", ""))/1000
		return self.curr_temp

class Fan:
	def __init__(self):
		self.desired_rpm = 0.0	# desired fan pwm signal in %
		self.last_rpm = 0.0		# last fan pwm signal in %
		self.rpm = 0.0			# rotational speed of fan in rpm
		self.pwm_pin = None
		self.t0 = time.time()	# timing variable to determine rpm

	def calcrpm(self, channel):
		# interrupt function that should calculate the rpm from tacho signal, but sometimes does not work due to interrupt
		t1 = time.time()		# get current time
		try:
			# self.rpm = (60 / (t1-self.t0)) # This is the normal formula to calculate rpm
			self.rpm = (30 / (t1-self.t0)) # Since there are two flanks per rotation we need to half it
		except ZeroDivisionError: pass
		finally: self.t0 = t1

	def testFan(self, killer):
		fan.pwm_pin.ChangeDutyCycle(100)	# set fan to fully on
		time.sleep(1)						# wait for fan to stabilize
		if(not self.rpm > 1000):			# check if fan is blocked -> at least that is what happened in my case
			os.system('echo \'test: Fancontrol: Warning fan might be blocked!\' | wall')	# announce error
			killer.thread_dont_terminate = False	# terminate script
		elif(not self.rpm):							# check if fan is broken
			os.system('echo \'test: Fancontrol: Warning fan might be broken!\' | wall')	# announce error
			killer.thread_dont_terminate = False	# terminate script
		fan.pwm_pin.ChangeDutyCycle(0)				# turn fan off

	def increase_rpm(self):
		if self.desired_rpm < 30: self.desired_rpm = 30
		elif self.desired_rpm < 100: self.desired_rpm += 5

	def decrease_rpm(self):
		if self.desired_rpm > 30: self.desired_rpm -= 5

class GracefulKiller:
	# class helping with killing signals so gpio's can be cleaned up
	thread_dont_terminate = True
	def __init__(self):
		signal.signal(signal.SIGINT, self.exit_gracefully)
		signal.signal(signal.SIGTERM, self.exit_gracefully)

	def exit_gracefully(self, signum, frame):
		self.thread_dont_terminate = False

# Configuration
FAN_PWM_GPIO = 19			# gpio pin the fan is connected to
FAN_SPEED_GPIO	= 26		# gpio pin the fan tachometer is connected to
PWM_FREQUENCY = 20			# frequency of the pwm signal to control the fan with
resources = [CPU(40)] # Disk(30, "sda")
fan = Fan()

gpio.setmode(gpio.BCM)				 # Select pin reference
gpio.setup(FAN_SPEED_GPIO, gpio.IN, pull_up_down = gpio.PUD_UP) # Declare fan speed pin as input and activate internal pullup resistor

# Add aboth function as interrupt to tacho pin on rising edges (can also be falling does not matter)
gpio.add_event_detect(FAN_SPEED_GPIO, gpio.RISING, callback = fan.calcrpm) # bouncetime=200 (in ms) to avoid "switch bounce"


if __name__ == '__main__':
	gpio.setup(FAN_PWM_GPIO, gpio.OUT)	 # Declare pwm fan pin as output
	fan.pwm_pin = gpio.PWM(FAN_PWM_GPIO, PWM_FREQUENCY) # Setup pwm on fan pin
	fan.pwm_pin.start(0) 				 # Setup fan pwm to start with 0% duty cycle

	killer = GracefulKiller()
	fan.testFan(killer)		# test the fan
	for resource in resources:
		resource.getTemp()

	# main loop
	while killer.thread_dont_terminate:
		if(fan.rpm == 0 and fan.desired_rpm > 0):	# check if fan is dead
			os.system('echo \'in main: Fancontrol: Warning fan might be broken!\' | wall')
			killer.thread_dont_terminate = False	# stop everything
			fan.pwm_pin.ChangeDutyCycle(0)			# turn fan off
			break

		fanOrders = set()
		for resource in resources:
			resource.getTemp()		# get cpu and disk temperature
			fanOrders.add(resource.ordersForFan())

		if 1 in fanOrders: fan.increase_rpm()	 # if anyone wants to increase speed
		elif -1 in fanOrders: fan.decrease_rpm() # if anyone wants to decrease speed
		else: fan.desired_rpm = 0				 # if everyone feels ok – turn off the fan

		if(fan.desired_rpm != fan.last_rpm):	# change duty cycle if changed
			fan.last_rpm = fan.desired_rpm
			fan.pwm_pin.ChangeDutyCycle(fan.desired_rpm)

		# print ("CPU: %d HDD: %d Fan: %d RPM: %d" % (resources[0].curr_temp, resources[1].curr_temp, fan.desired_rpm, fan.rpm))
		print ("CPU: %d Fan: %d RPM: %d" % (resources[0].curr_temp, fan.desired_rpm, fan.rpm))
		fan.rpm = 0		# reset rpm
		time.sleep(5)

	gpio.cleanup()	# cleanup gpio's
	print("Fancontrol: Stopping fancontrol")
