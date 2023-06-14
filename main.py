import socket
import select
import board
import stepper
import time
import adafruit_mprls
import threading
import queue


class AppState:
    runMotors = False
    """Whether or not the motors are/should be running."""
    priming = False
    """Whether or not the motors are/should be priming."""
    debugging = False
    """Whether or not to print debugging information."""
    send_pressure_sensor_update = True
    """Whether or not to send pressure sensor updates to the client."""
    connection = None
    """The connection to the client."""
    scale_multiplier = 1.0
    """The multiplier to apply to the data when moving."""
    positional_data_index = 0
    """The index of the positional data to use."""
    priming_speed = 0
    """The speed to run the motors at while priming."""
    priming_iterations_since_last_update = 0
    """The number of iterations since the last priming update."""
    stepper_target_position = 0
    """The target position of the stepper motor in steps relative to start position as 0."""
    pressure_sensor_update_queue = queue.Queue(maxsize=10)
    """The queue of pressure sensor updates to send to the client."""
    last_priming_update = 0

    data_time_step_ms = 10
    """The time in milliseconds between movement data points."""

    stepper = None
    i2c = None
    mpr = None
    comm = None

    def __init__(self):
        self.version = "1.1.0"
        self.last_step_timestamp_ms = -1
        """The last time the stepper motor performed a step (ms since epoch)."""
        self.scale_multiplier = 1.0
        self.positional_data = []
        self.data_time_step_ms = 10
        """The time in milliseconds between data points."""
        self.last_priming_update = 0
        self.last_pressure_sensor_update = 0
        self.app_start_time_ms = time.time() * 1000
        self.last_update = -1
        """The last time the stepper motor target position was updated (ms since epoch)."""
        self.stepper = stepper.MyStepperController(
            step_pin=23,
            direction_pin=24,
            enable_pin=25)

        i2c = board.I2C()
        # Connect to default over I2C
        self.mpr = adafruit_mprls.MPRLS(i2c, psi_min=0, psi_max=25)
        self.send_pressure_sensor_update = True


class Communications:
    read_queue = []
    connection = None
    socket = None
    read_buffer = ""

    def __init__(self):
        self.connection = None
        self.read_queue = []
        self.write_queue = []
        self.read_handle = None
        self.write_handle = None

        self.connect()

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        self.connection.close()
        self.socket.close()

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow for quick reuse of the socket.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', 9999))
        self.socket.listen(1)

        print("Waiting for a connection")
        self.connection, address = self.socket.accept()
        # Set to non-blocking for the recv calls hereafter.
        self.socket.setblocking(False)
        print("Connection from " + str(address))

    def send_data(self, data):
        self.write_queue.insert(0, data)

        if len(self.write_queue) > 200:
            self.write_queue = ["E:Write queue overflow!"]
            app.comm.socket.setblocking(True)
            self.process_outgoing()
            app.comm.socket.setblocking(False)

    def process_streams(self):
        # Fetch incoming data from stream and queue it.
        self.process_incoming()
        # Send outgoing data from queue to stream.
        self.process_outgoing()

    def process_outgoing(self):
        # Check if the sockets are ready on the connection.
        read_handle, write_handle, exception_handle = select.select(
            [],
            [self.connection],
            [], 0)

        if self.connection in exception_handle:
            print("Connection closed!")
            self.connection.close()
            self.connect()
            return

        # If there is data to write...
        if self.connection in write_handle:
            # While there is data in the write queue...
            while len(self.write_queue) > 0:
                # Send the data.
                self.connection.send(self.write_queue.pop().encode())

    def process_incoming(self):
        # Check if the sockets are ready on the connection.
        read_handle, write_handle, exception_handle = select.select(
            [self.connection],
            [],
            [], 0)

        if self.connection in exception_handle:
            print("Connection closed!")
            self.connection.close()
            self.connect()
            return

        # If there is data to read...
        if self.connection in read_handle:
            # Receive data, note that this does not block if no data is available.
            try:
                data = self.connection.recv(2048)
                if not data:
                    print("Connection closed!")
                    self.connection.close()
                    self.connect()
                    return
                self.read_buffer += data.decode('utf-8')
            except BlockingIOError:
                pass
            except UnicodeDecodeError:
                pass
            except ConnectionResetError:
                pass

            # While there are newlines present in the read buffer...
            while self.read_buffer.find("\n") != -1:
                new_item = self.read_buffer[:self.read_buffer.find("\n")]
                # Append the data to the read queue (without the newline).
                self.read_queue.append(new_item)
                if app.debugging:
                    print("[Input]:" + new_item)
                # Remove the processed data from the buffer.
                self.read_buffer = self.read_buffer[self.read_buffer.find("\n") + 1:]


# Create an instance of the app state.
app = AppState()


def logger(text):
    app.comm.send_data(text + "\n")
    print(text)


def update_step_frequency(data: int):
    app.data_time_step_ms = data
    # Convert app.data_time_step_ms (wavelength) to frequency
    frequency = (1000 / app.data_time_step_ms)

    logger(
        "I:Step frequency updated to " + str(frequency) + " Hz.," +
        " step length is " + str(app.data_time_step_ms) + " ms.")


def set_new_home_position():
    """Set the current position as the new home position.
    This will reset the positional data index to 0.
    """
    app.stepper.set_current_position(0)
    if app.debugging:
        logger("I:New home position set.")


def load_positional_data(line_count: int):
    # (Re)initialize the positional data.
    app.positional_data = []
    index = 0

    # Fetch data from stream and queue it.
    while True:
        app.comm.process_incoming()

        # If we have data in the queue, process it.
        if len(app.comm.read_queue) > 0:
            # Get the first item in the queue.
            line = app.comm.read_queue.pop(0).strip()
            if len(line) > 0:
                app.positional_data.append(float(line))
                if app.debugging:
                    print("[DATA]: Received " + line)
            else:
                # If the line is empty, we have reached the end of the data.
                # if line_count == len(app.positional_data):
                # Send acknowledgement to client.
                logger("D:" + str(len(app.positional_data)))
                # else:
                #     logger("E:Data error, expected:" + str(line_count) + " got:" + str(len(app.positional_data)))
                # Set the "home" to whatever the first entry in the datafile is.
                # This will avoid the stepper logic trying to "catch up" to start.
                app.stepper.set_current_position(app.positional_data[0])
                if app.debugging:
                    # Print the data if debugging is enabled.
                    for line in app.positional_data:
                        logger("I: %f" % line)
                return


def update_priming(data: int):
    """
    Update the priming speed.
    This is the speed at which the priming operation will run.

    Parameters:
        data (int): The priming speed in steps per second.
    """

    # Set the priming speed. Note the negative assignment, this is a UX change.
    app.priming_speed = -data
    if app.debugging:
        logger("I:Priming speed updated to " + str(data) + " steps per second.")


def update_scale_multiplier(data):
    """
    Update the scale multiplier.
    This is used to scale the positional data to the correct size.

    Parameters:
        data (float): The scale multiplier.
    """
    app.scale_multiplier = data
    if app.debugging:
        logger("I:Scale multiplier updated to " + str(data) + ".")


def process_input(line):
    if len(line) == 0:
        return

    # Get first character of the line.
    cmd = line[0]
    # Fetch the rest of the line after : character and remove newline.
    data = line[2:].strip()

    # Enable/disable (D)ebugging.
    if cmd == 'D':
        if data == "T":
            app.debugging = True
            logger("I:Debugging enabled.")
        else:
            app.debugging = False
            logger("I:Debugging disabled.")
    # Update the step (F)requency - this is the ms between steps.
    elif cmd == 'F':
        update_step_frequency(int(data))
    # Set new (H)ome position.
    elif cmd == 'H':
        set_new_home_position()
    # (L)oad data
    elif cmd == 'L':
        load_positional_data(data)
    # (P)rime pump
    elif cmd == 'P':
        app.priming = True
        app.stepper.enable_outputs()
        # Convert the numeric bit to an integer.
        update_priming(int(data))
    # (R)un application.
    elif cmd == 'R':
        app.runMotors = True
        app.stepper.enable_outputs()
        logger("I:Application started")
    # (S)top application.
    elif cmd == 'S':
        app.runMotors = False
        app.priming = False
        app.stepper.disable_outputs()
        logger("I:Application stopped")
    # Update (V)elocity.
    elif cmd == 'V':
        logger("E:Velocity update not implemented.")
    # Update scale (X) multiplier for positional data
    elif cmd == 'X':
        update_scale_multiplier(float(data))
    #
    elif cmd == 'Z':
        if data == "T":
            logger("I:Suspending pressure sensor data updates")
            app.send_pressure_sensor_update = False
        else:
            logger("I:Resuming pressure sensor data updates")
            app.send_pressure_sensor_update = True
    elif cmd == '!':
        from subprocess import call
        call("sudo shutdown -h now", shell=True)
    # (E)rror.
    elif cmd == 'E':
        logger("E:Received error from application: " + data)
    else:
        logger("E:Received unknown command/data: " + line.strip())


def current_time_in_ms() -> float:
    """Get the current time in milliseconds."""
    return (time.time() * 1000) - app.app_start_time_ms


def update_target_position():
    """Update the target position of the stepper motor.
    This will update the target position based on the current index of the positional data."""

    # Get the current time in milliseconds.
    current_time_ms = current_time_in_ms()

    # If we have positional data to process...
    if len(app.positional_data) > 0:
        # If we have waited long enough, update the target position.
        if (current_time_ms - app.last_update) > app.data_time_step_ms:
            # Update the target position.
            app.stepper_target_position = round(app.positional_data[app.positional_data_index] * app.scale_multiplier)

            # If debugging is enabled, print debugging information.
            if app.debugging:
                logger("I:" + str(current_time_ms) + "," +
                       str(app.stepper.current_position()) + "," +
                       str(app.stepper_target_position) + "," +
                       str(app.positional_data[app.positional_data_index] * app.scale_multiplier))

            # Increment the index.
            app.positional_data_index += 1
            # If we have reached the end of the data, stop the motors.
            if app.positional_data_index >= len(app.positional_data):
                app.positional_data_index = 0
                print("I:" + str(current_time_ms) + " Iteration complete.")

            app.last_update = current_time_ms


def update_stepper_movement():
    """Update the stepper motor movement.
    This will update the stepper motor movement based on the current target position and current position."""

    # Issue a step on the motor if the move_to target and current_position suggests it should.
    if app.stepper_target_position != app.stepper.current_position():
        # Calculate the delta between the target position and the current position.
        delta_y = app.stepper_target_position - app.stepper.current_position()
        # Calculate the delta in milliseconds since the last step.
        delta_px = (current_time_in_ms()) - app.last_step_timestamp_ms
        # Calculate the number of steps needed to reach target.
        delta_y_t = round((delta_y * delta_px) / app.data_time_step_ms)
        # If the delta is not 0, issue a step.
        if delta_y_t != 0:
            app.stepper.step(delta_y_t > 0)
            app.last_step_timestamp_ms = current_time_in_ms()


def update_priming_position():
    percent_of_steps_to_take = int(round(abs(app.priming_speed)))

    # If we have waited long enough, update the target position.
    if (current_time_in_ms() - app.last_priming_update) > 0.05:
        app.last_priming_update = current_time_in_ms()

        app.priming_iterations_since_last_update += 1

        if app.priming_iterations_since_last_update > (100 - percent_of_steps_to_take):
            app.priming_iterations_since_last_update = 0
            if app.priming_speed > 0:
                app.stepper.step(True)
            elif app.priming_speed < 0:
                app.stepper.step(False)


def main_loop_cycle():
    """Main loop cycle."""

    # Process any incoming/outgoing data.
    app.comm.process_streams()

    # If we have data in the queue, process it.
    if len(app.comm.read_queue) > 0:
        process_input(app.comm.read_queue.pop(0))

    show_pressure_sensor_update()

    # Update runtime state and feedback.
    if app.runMotors:
        update_target_position()
        update_stepper_movement()

    if app.priming:
        update_priming_position()


def get_pressure_sensor_data():
    while True:
        # If we have waited long enough, update the pressure sensor queue.
        if (current_time_in_ms() - app.last_pressure_sensor_update) > 0.1:
            app.last_pressure_sensor_update = current_time_in_ms()

            # Read the pressure from the sensor.
            pressure_h_pa = app.mpr.pressure

            # Convert the pressure to mmHg.
            pressure_mm_hg = pressure_h_pa * 0.7500615613

            try:
                app.pressure_sensor_update_queue.put_nowait(pressure_mm_hg)
            except queue.Full:
                pass


def show_pressure_sensor_update():
    """Show an update from the pressure sensor."""

    # If data return is not enabled, return.
    if app.send_pressure_sensor_update is False:
        return

    try:
        pressure_mm_hg = app.pressure_sensor_update_queue.get_nowait()
        # Print the pressure to the serial port.
        logger("P:" + str(pressure_mm_hg))
    except queue.Empty:
        pass


t1 = threading.Thread(target=get_pressure_sensor_data, name='t1')
t1.start()

while True:
    # Wait for a connection
    app.comm = Communications()

    # If we lose connection, drop out of the loop.
    while app.comm.connection is not None:
        main_loop_cycle()

    # Close the connection
    app.comm.socket.close()
    print("Connection closed")
