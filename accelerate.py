from __future__ import print_function

import collections
import time
import traceback

import smbus
import gopigo

TRIM = 0#5#0
INITIAL_SPEED = 50
MAX_SPEED = 200
MIN_SPEED = 30

INC_CONST = 100.0

CRITICAL_DISTANCE = 10
SAFE_DISTANCE = 2 * CRITICAL_DISTANCE
ALERT_DISTANCE = 3 * SAFE_DISTANCE
SLOWDOWN_SPAN = (4.0/ 5.0) * (SAFE_DISTANCE - CRITICAL_DISTANCE)

SLOWING_DECCELLERATION = 50#100 # power units/ second
SPEED_ACCELERATION = 40#100

STOP_THRESHOLD = 0.01

SAMPLE_SIZE = 10#20
ALERT_THRESHOLD = 0.01

USS_ERROR = "USS_ERROR"
NOTHING_FOUND = "NOTHING_FOUND"

###############################################

ADDRESS = 0x08
ENC_READ_CMD = [53]

LEFT = 0
RIGHT = 1

USS = 15

BUS = smbus.SMBus(1)

def write_i2c_block(address, block):
    try:
        op = BUS.write_i2c_block_data(address, 1, block)
        time.sleep(0.005)
        return op
    except IOError:
        return -1
    return 1

def enc_read(motor):
    write_i2c_block(ADDRESS, ENC_READ_CMD+[motor, 0, 0])
    #time.sleep(0.01)
    #time.sleep(0.08)
    try:
        b1 = BUS.read_byte(ADDRESS)
        b2 = BUS.read_byte(ADDRESS)
    except IOError:
        return -1
    if b1 != -1 and b2 != -1:
        v = b1 * 256 + b2
        return v
    else:
        return -1

US_CMD = [117]

def us_dist(pin):
    write_i2c_block(ADDRESS, US_CMD+[pin, 0, 0])
    time.sleep(0.01)
    #time.sleep(0.08)
    try:
        b1 = BUS.read_byte(ADDRESS)
        b2 = BUS.read_byte(ADDRESS)
    except IOError:
        return -1
    if b1 != -1 and b2 != -1:
        v = b1 * 256 + b2
        return v
    else:
        return -1

###############################################

def get_inc(speed):
    #return 10
    if speed < 0.1 and speed > -0.1:
        return 0
    else:
        return (9.0 / (speed / INC_CONST)) / 1.5

def get_deccelleration(speed):
    return (speed ** 2.0) / (2.0 * SLOWDOWN_SPAN)

#def main(command_queue):
def main():
    speed = INITIAL_SPEED

    gopigo.trim_write(TRIM)

    time.sleep(0.1)
    print("Volt: " + str(gopigo.volt()))

    time.sleep(0.1)
    initial_ticks_left = enc_read(LEFT)
    time.sleep(0.1)
    initial_ticks_right = enc_read(RIGHT)

    print("Initial\tL: " + str(initial_ticks_left) + "\tR: " + str(initial_ticks_right))

    print("Critical: " + str(CRITICAL_DISTANCE))
    print("Safe:     " + str(SAFE_DISTANCE))
    print("Alert:    " + str(ALERT_DISTANCE))

    dists = collections.deque(maxlen=SAMPLE_SIZE)
    dts = collections.deque(maxlen=SAMPLE_SIZE)

    elapsed_ticks_left = 0
    elapsed_ticks_right = 0

    try:
        gopigo.set_speed(0)
        gopigo.fwd()

        t = time.time()
        while True:
            if speed < 0:
                speed = 0

            print("========================")
            #if not command_queue.empty():
            #   comm = command_queue.get()
            #   global MAX_SPEED
            #   global SAFE_DISTANCE
            #   MAX_SPEED = comm[0]
            #   SAFE_DISTANCE = comm[1]

            #   print(comm)

            dt = time.time() - t
            t = time.time()

            #time.sleep(0.1)

            print("Time: " + str(dt))

            #time.sleep(0.005)
            dist = get_dist()
            #time.sleep(0.005)
            print("Dist: " + str(dist))

            if not isinstance(dist, str):
                dists.append(float(dist))
                dts.append(float(dt))

            rel_speed = None
            if len(dists) > 9:
                rel_speed = calculate_relative_speed(dists, dts)
                print("Rel speed: " + str(rel_speed))

            if (isinstance(dist, str) and dist != NOTHING_FOUND) or dist < CRITICAL_DISTANCE:
                print("< Critical")
                stop_until_safe_distance()
                speed = 0
                t = time.time()
            elif dist < SAFE_DISTANCE:
                print("< Safe")
                if speed > STOP_THRESHOLD:
                    #speed = speed - dt * SPEED_DECCELLERATION
                    speed = speed - dt * get_deccelleration(speed)
                else:
                    speed = 0
            elif speed > MAX_SPEED:
                print("Slowing down")
                speed = speed - dt * SLOWING_DECCELLERATION
            elif dist < ALERT_DISTANCE and rel_speed is not None:
                if rel_speed > ALERT_THRESHOLD:
                    print("Alert speeding")
                    speed = speed + dt * SPEED_ACCELERATION
                elif rel_speed < -ALERT_THRESHOLD:
                    print("Alert slowing")
                    speed = speed - dt * SLOWING_DECCELLERATION
                    if speed < MIN_SPEED:
                        speed = MIN_SPEED
                else:
                    print("Alert stable")
            elif speed < MAX_SPEED:
                print("Speeding up")
                speed = speed + dt * SPEED_ACCELERATION
                #speed = speed - dt * get_deccelleration(speed)


            elapsed_ticks_left, elapsed_ticks_right = \
                read_enc_ticks(initial_ticks_left, initial_ticks_right)

            print("L: " + str(elapsed_ticks_left) + "\tR: " + str(elapsed_ticks_right))

            if elapsed_ticks_left > elapsed_ticks_right:
                print("Right slow")
                set_speed_lr(speed, -get_inc(speed), get_inc(speed))
            elif elapsed_ticks_left < elapsed_ticks_right:
                print("Left slow")
                set_speed_lr(speed, get_inc(speed), -get_inc(speed))
            else:
                print("Equal")
                set_speed_lr(speed, 0, 0)

            print("Speed: " + str(speed))

    except (KeyboardInterrupt, Exception):
        traceback.print_exc()
        gopigo.stop()
    gopigo.stop()

def read_enc_ticks(initial_ticks_left, initial_ticks_right):
    time.sleep(0.001)
    elapsed_ticks_left = enc_read(LEFT) - initial_ticks_left
    #time.sleep(0.005)
    time.sleep(0.001)
    elapsed_ticks_right = enc_read(RIGHT) - initial_ticks_right
    #time.sleep(0.005)

    return (elapsed_ticks_left, elapsed_ticks_right)

def set_speed_lr(speed, l_diff, r_diff):
    print(l_diff)
    if speed >= MIN_SPEED:
        gopigo.set_left_speed(int(speed + l_diff))
        gopigo.set_right_speed(int(speed + r_diff))
    else:
        gopigo.set_left_speed(0)
        gopigo.set_right_speed(0)

def calculate_relative_speed(dists, dts):
    old_dist = sum(list(dists)[0:len(dists) / 2]) / (len(dists) / 2)
    new_dist = sum(list(dists)[len(dists) / 2:]) / (len(dists) / 2)

    old_dt = sum(list(dts)[0:len(dts) / 2])
    new_dt = sum(list(dts)[len(dts) / 2:])

    rel_speed = (new_dist - old_dist) / ((new_dt + old_dt) / 2.0)

    return rel_speed

def get_dist():
    time.sleep(0.01)
    dist = us_dist(USS)

    if dist == -1:
        return USS_ERROR
    elif dist == 0 or dist == 1:
        return NOTHING_FOUND
    else:
        return dist

def stop_until_safe_distance():
    gopigo.stop()
    dist = get_dist()
    while (isinstance(dist, str) and dist != NOTHING_FOUND) or dist < SAFE_DISTANCE:
        dist = get_dist()

    gopigo.set_speed(0)
    gopigo.fwd()

if __name__ == "__main__":
    main()
