import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)  # choose BCM or BOARD
GPIO.setup(23, GPIO.OUT)
GPIO.setup(24, GPIO.OUT)
GPIO.setup(25, GPIO.OUT)

GPIO.output(25, GPIO.LOW)

GPIO.output(24, GPIO.HIGH)

x = 0
while x < 1000:
    time.sleep(1)
    GPIO.output(23, GPIO.HIGH)
    # Stay active for the pulse width.
    time.sleep(1)
    # End the pulse.
    GPIO.output(23, GPIO.LOW)
    x = x + 1

GPIO.cleanup()
