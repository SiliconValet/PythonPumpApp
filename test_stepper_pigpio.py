import sys
import time
import advpistepper
import pigpio

pi = pigpio.pi()

pi.set_mode(16, pigpio.OUTPUT)
pi.set_mode(20, pigpio.OUTPUT)
pi.set_mode(21, pigpio.OUTPUT)

print("About to blink")
for t in range(0, 3):
    pi.write(16, 1)
    pi.write(20, 1)
    pi.write(21, 0)
    time.sleep(0.3)
    pi.write(16, 1)
    pi.write(20, 0)
    pi.write(21, 1)
    time.sleep(0.3)
    pi.write(16, 0)
    pi.write(20, 1)
    pi.write(21, 1)
    time.sleep(0.3)



# Disable all pins
pi.write(16, 0)
pi.write(20, 0)
pi.write(21, 0)
print("Done blinking")

p = {
    advpistepper.STEP_PULSE_LENGTH: 10,
    advpistepper.STEP_PULSE_DELAY: 10,
}

driver = advpistepper.DriverStepDirGeneric(
    step_pin=23,
    dir_pin=24,
    parameters=p)
stepper = advpistepper.AdvPiStepper(driver)

stepper.microsteps = 1


print("About to move to 400")
stepper.move_to(
    position=200,
    speed=30,
    block=True)
print("About to move to 200")
stepper.move_to(
    position=100,
    speed=30,
    block=True)
print("Done moving to 200")

#stepper.stop
stepper.release()
print("Done releasing")
stepper.close()
time.sleep(0.1)
quit(0)
