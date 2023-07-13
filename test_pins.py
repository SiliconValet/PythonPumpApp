import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)  # choose BCM or BOARD

GPIO.cleanup()

GPIO.setup(23, GPIO.OUT) # STE
GPIO.setup(24, GPIO.OUT) # DIR
GPIO.setup(25, GPIO.OUT) # ENA

GPIO.output(25, GPIO.LOW)

GPIO.output(24, GPIO.HIGH)
GPIO.output(23, GPIO.LOW)

pin = 23

x = 0
while x < 1000:
    time.sleep(1)
    GPIO.output(pin, GPIO.HIGH)
    # Stay active for the pulse width.
    time.sleep(1)
    # End the pulse.
    GPIO.output(pin, GPIO.LOW)
    x = x + 1

GPIO.cleanup()
