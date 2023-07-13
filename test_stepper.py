import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)  # choose BCM or BOARD
GPIO.setup(23, GPIO.OUT)  # ste
GPIO.setup(24, GPIO.OUT)  # dir
GPIO.setup(25, GPIO.OUT)  # ena

GPIO.output(25, GPIO.LOW)  # ena low

GPIO.output(24, GPIO.LOW)  # dir low
time.sleep(2)
print("One direction")

x = 0
while x < 1000:
    time.sleep(0.001)
    GPIO.output(23, GPIO.HIGH)
    # Stay active for the pulse width.
    time.sleep(10 / 1000000)
    # End the pulse.
    GPIO.output(23, GPIO.LOW)
    x = x + 1

GPIO.output(24, GPIO.HIGH)  # dir high
time.sleep(2)
print("Other direction")

x=0
while x < 1000:
    time.sleep(0.001)
    GPIO.output(23, GPIO.HIGH)
    # Stay active for the pulse width.
    time.sleep(10 / 1000000)
    # End the pulse.
    GPIO.output(23, GPIO.LOW)
    x = x + 1

GPIO.cleanup()
