import time
import RPi.GPIO as GPIO


class MyStepperController:
    debugging = False

    def __init__(self, step_pin: int, direction_pin: int, enable_pin: int):
        self._last_set_position = 0
        self.last_step_timestamp_ms = 0
        self._current_position = 0
        """The current position of the stepper motor in steps relative to start position as 0."""
        self._init_delay_ms = 50
        """The delay in milliseconds to wait after initialization before allowing movement."""
        self.step_delay_microseconds = 5
        """The time in microseconds to delay between steps to allow motor time to react."""
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

        # setup GPIO
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
        time.sleep(self._init_delay_ms / 1000)

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

        GPIO.output(self.step_pin, GPIO.HIGH)
        # Stay active for the pulse width.
        time.sleep(self.step_delay_microseconds / 1000000)
        # End the pulse.
        GPIO.output(self.step_pin, GPIO.LOW)

        time.sleep(self.step_delay_microseconds / 1000000)

        if direction:
            self._current_position += 1
        else:
            self._current_position -= 1
