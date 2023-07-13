import time
import RPi.GPIO as GPIO
# import pigpio


class MyStepperController:
    debugging = False

    def __init__(self, step_pin: int, direction_pin: int, enable_pin: int):
        self._last_set_position = 0
        self.last_step_timestamp_ms = 0
        self._current_position = 0
        """The current position of the stepper motor in steps relative to start position as 0."""
        self.init_delay_microseconds = 50
        """The delay in microseconds to wait after initialization before allowing movement."""
        self.low_level_delay_microseconds = 2.5
        """The time in microseconds to delay between steps to allow motor time to react."""
        self.pulse_delay_microseconds = 15
        """The time in microseconds to delay after init to allow motor time to react."""
        self._target_position = 0
        """The target position of the stepper motor in steps relative to start position as 0."""
        self.step_pin = step_pin
        """The GPIO pin number for the step pin."""
        self.direction_pin = direction_pin
        """The GPIO pin number for the direction pin."""
        self.enable_pin = enable_pin
        """The GPIO pin number for the enable pin."""
        self.last_direction = 0
        """The last direction the motor was moving."""
        self.pi = pigpio.pi()
        """The pigpio instance for controlling the stepper motor."""

        self.use_pigpio = True

        # # Check if pigpio is available.
        # if isinstance(self.pi, pigpio.pi):
        #     pi.set_mode(self.step_pin, pigpio.OUTPUT)
        #     pi.set_mode(self.direction_pin, pigpio.OUTPUT)
        #     pi.set_mode(self.enable_pin, pigpio.OUTPUT)
        # else:
        #     print("PigPio not found/connecting. Using GPIO instead.")
        #     self.use_pigpio = False

        # if not self.use_pigpio:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)  # choose BCM or BOARD
        GPIO.setup(self.step_pin, GPIO.OUT)
        GPIO.setup(self.direction_pin, GPIO.OUT)
        GPIO.setup(self.enable_pin, GPIO.OUT)

        # Set direction to forward.
        GPIO.output(self.direction_pin, GPIO.LOW)

    def current_position(self) -> int:
        return self._current_position

    def get_target_position(self) -> int:
        return self._target_position

    def enable_outputs(self):
        GPIO.output(self.enable_pin, GPIO.LOW)
        # This is probably redundant, but it's cheap.
        time.sleep(self.init_delay_microseconds / 1000000.0)

    def disable_outputs(self):
        GPIO.output(self.enable_pin, GPIO.HIGH)

    def move_to(self, position):
        self._last_set_position = self._current_position
        self._target_position = position
        return

    def set_current_position(self, position=0):
        self._current_position = int(round(position))

    def step(self, direction):
        """Perform one step in the indicated direction. Private function."""

        if self.debugging:
            print("Stepping in direction: " + str(direction))
            if direction:
                self._current_position += 1
            else:
                self._current_position -= 1
            return

        # Set the direction pin if it's changed. This is a cheap operation compared to the GPIO call.
        if direction != self.last_direction:
            GPIO.output(self.direction_pin, GPIO.HIGH if direction else GPIO.LOW)
            self.last_direction = direction
            # Delay long enough to allow the motor to react to the direction change.
            time.sleep(self.pulse_delay_microseconds / 1000000.0)

        GPIO.output(self.step_pin, GPIO.HIGH)
        # Stay active for the pulse width.
        time.sleep(self.pulse_delay_microseconds / 1000000.0)
        # End the pulse.
        GPIO.output(self.step_pin, GPIO.LOW)

        # Delay long enough to allow the motor to react to the pulse.
        time.sleep(self.pulse_delay_microseconds / 1000000.0)

        # Update the current position.
        if direction:
            self._current_position += 1
        else:
            self._current_position -= 1
