#!/usr/bin/python
import RPi.GPIO as GPIO
import os
import signal
import time

# Basic configuration
c_FAN = 26					# gpio pin the fan is connected to
c_FAN_TACHO	= 19			# gpio pin the fan tachometer is connected to
c_MIN_TEMPERATURE = 45		# temperature in degrees c when fan should turn on
c_TEMPERATURE_OFFSET = 2	# temperarute offset in degrees c when fan should turn off
c_HARDDRIVE = "sda"			# name of your harddrive

# Advanced configuration
c_PWM_FREQUENCY = 20		# frequency of the pwm signal to control the fan with

# Variables: Do not touch!
c_TEMPERATURE_OFFSET = c_MIN_TEMPERATURE - c_TEMPERATURE_OFFSET
last_cpu = 0		# last measured cpu temperarute
last_hdd = 0		# last measured hdd temperarute
desired_fan = 0		# desired fan pwm signal in %
last_fan = 0		# last fan pwm signal in %
rpm = 0.0			# rotational speed of fan in rpm
t0 = time.time()	# timing variable to determine rpm


# Select pin reference
GPIO.setmode(GPIO.BCM)
# Declare fan tacho pin as input and activate internal pullup resistor
GPIO.setup(c_FAN_TACHO, GPIO.IN, pull_up_down = GPIO.PUD_UP)
# Declare fan pin as output
GPIO.setup(c_FAN, GPIO.OUT)
# Setup pwm on fan pin
fan = GPIO.PWM(c_FAN, c_PWM_FREQUENCY)
# Setup fan pwm to start with 0 % duty cycle
fan.start(0)

# interrupt function that should calculate the rpm from tacho signal, but sometimes does not work due to interrupt
def calcrpm(channel):
	global t0			# get global variable
	global rpm			# get global variable
	t1 = time.time()	# get current time
	try:
		#rpm = (60 / (t1-t0)) # This is the normal formula to calculate rpm
		rpm = (30 / (t1-t0)) # Since there are two flanks per rotation we need to half it
	except ZeroDivisionError:
		pass
	t0 = t1	# save time this was called

# Add aboth function as interrupt to tacho pin on rising edges (can also be falling does not matter)
GPIO.add_event_detect(c_FAN_TACHO, GPIO.RISING, callback = calcrpm)



# function to get the cpu temperarute
def getCPUTemp():
	f = open("/sys/class/thermal/thermal_zone0/temp")
	CPUTemp = f.read()
	f.close()
	return int(CPUTemp.replace("\n",""))/1000	# remove return from result, cast to int and divide by 1000

# function to get the hdd temperarute
def getHDDTemp():
	res = os.popen("sudo smartctl -d sat --all /dev/%s | grep Temperature_Celsius | awk '{print $10}'" % c_HARDDRIVE).readline()
	return int(res)	# cast result to int

def testFan(killer):
	fan.ChangeDutyCycle(100)	# set fan to fully on
	time.sleep(1)				# wait for fan to stabilize
	if(not rpm > 1000):			# check if fan is blocked -> at least that is what happened in my case
		os.system('echo \'Fancontrol: Warning fan might be blocked!\' | wall')	# announce error
		killer.thread_dont_terminate = False	# terminate script
	elif(not rpm):	# check if fan is broken
		os.system('echo \'Fancontrol: Warning fan might be broken!\' | wall')	# announce error
		killer.thread_dont_terminate = False	# terminate script
	fan.ChangeDutyCycle(0)		# turn fan off

# class helping with killing signals so gpio's can be cleaned up
class GracefulKiller:
	thread_dont_terminate = True
	def __init__(self):
		signal.signal(signal.SIGINT, self.exit_gracefully)
		signal.signal(signal.SIGTERM, self.exit_gracefully)

	def exit_gracefully(self, signum, frame):
		self.thread_dont_terminate = False

# main function
if __name__ == '__main__':
	killer = GracefulKiller()	# get a GracefulKiller
	testFan(killer)				# test the fan
	while killer.thread_dont_terminate:	# main loop
		cpu = getCPUTemp()	# get cpu temperature
		hdd = getHDDTemp()	# get hdd temperature
		if(rpm == 0 and desired_fan > 0):	# check if fan is dead
			os.system('echo \'Fancontrol: Warning fan might be broken!\' | wall')	# announce error
			killer.thread_dont_terminate = False	# stop everything
			fan.ChangeDutyCycle(0)	# turn fan off
			break	# stop loop
		if (cpu < c_TEMPERATURE_OFFSET and hdd < c_TEMPERATURE_OFFSET):	# check if temperature is low enough to turn off
			desired_fan = 0	# set desired fan speed to 0 aka off
		elif (cpu > c_MIN_TEMPERATURE or hdd > c_MIN_TEMPERATURE):	# check if temperature exceeded the set level
			if ((cpu >= last_cpu or hdd >= last_hdd) and desired_fan < 100):	# check if temperature is rising or staying the same
				if (desired_fan < 30):	# fan was off and minimum speed is 30% duty cycle
					desired_fan = 30
				else:	# increase speed, since we are not decreasing the temperature
					desired_fan += 5
			elif ((cpu < last_cpu or hdd < last_hdd) and desired_fan > 30):	# only if everything cools we can decrease the speed
				desired_fan -= 5
			print "CPU: %d HDD: %d Fan: %d RPM: %d" % (cpu, hdd, desired_fan, rpm)	# debug information
		if(desired_fan != last_fan):	# only change duty cycle when it changed
			last_fan = desired_fan
			fan.ChangeDutyCycle(desired_fan)

		last_cpu = cpu	# keep track of cpu temperature
		last_hdd = hdd	# keep track of hdd temperature
		rpm = 0			# reset rpm
		time.sleep(5)	# sleep for 5 seconds
	GPIO.cleanup()	# cleanup gpio's
 	print "Fancontrol: Stopping fancontrol" # print exit message
