import gopigo
import sys
import time

LEFT = 0
RIGHT = 1

SPEED = int(sys.argv[1])
INC = (SPEED / 100) * 10 #7#15

SAFE_DISTANCE = 45
USS = 15

TRIM = int(sys.argv[2])
CORRECTION = sys.argv[3] == "true"
print(CORRECTION)

# Might as well try this out, probably doesn't do anything though
gopigo.disable_encoders()
gopigo.enable_encoders()

gopigo.trim_write(TRIM)

ADDRESS = 0x08
ENC_READ_CMD = [53]

import smbus
bus = smbus.SMBus(1)

def write_i2c_block(address, block):
    try:
        op = bus.write_i2c_block_data(address, 1, block)
        time.sleep(0.005)
        return op
    except IOError:
        return -1
    return 1

def enc_read(motor):
    write_i2c_block(ADDRESS, ENC_READ_CMD+[motor,0,0])
    #time.sleep(0.01)
    #time.sleep(0.08)
    try:
        b1 = bus.read_byte(ADDRESS)
        b2 = bus.read_byte(ADDRESS)
    except IOError:
        return -1
    if b1 != -1 and b2 != -1:
        v = b1 * 256 + b2
        return v
    else:
        return -1

US_CMD = [117]

def us_dist(pin):
    write_i2c_block(ADDRESS, US_CMD+[pin,0,0])
    time.sleep(0.01)
    #time.sleep(0.08)
    try:
        b1 = bus.read_byte(ADDRESS)
        b2 = bus.read_byte(ADDRESS)
    except IOError:
        return -1
    if b1 != -1 and b2 != -1:
        v = b1 * 256 + b2
        return v
    else:
        return -1

time.sleep(0.1)
initial_ticks_left = enc_read(LEFT)
time.sleep(0.1)
initial_ticks_right = enc_read(RIGHT)

elapsed_ticks_left = 0
elapsed_ticks_right = 0

try:
    try:
        gopigo.set_speed(SPEED)
        gopigo.fwd()
        while True:
            #time.sleep(0.12)
            t = time.time()
            dist = us_dist(USS)
            print("Dist: " + str(dist))
            if dist < SAFE_DISTANCE:
                gopigo.stop()
                while dist < SAFE_DISTANCE:
                    dist = us_dist(USS)
		    time.sleep(0.01)
                gopigo.fwd()
            #time.sleep(0.1)
            elapsed_ticks_left = enc_read(LEFT) - initial_ticks_left
            #time.sleep(0.1)
            elapsed_ticks_right = enc_read(RIGHT) - initial_ticks_right

            print("L: " + str(elapsed_ticks_left) + "\tR: " + str(elapsed_ticks_right))

            if elapsed_ticks_left > elapsed_ticks_right:
                print("RIGHT SLOW")
                if CORRECTION:
                    gopigo.set_left_speed(SPEED - INC)
                    gopigo.set_right_speed(SPEED + INC)
            elif elapsed_ticks_left < elapsed_ticks_right:
                print("LEFT SLOW")
                if CORRECTION:
                    gopigo.set_left_speed(SPEED + INC)
                    gopigo.set_right_speed(SPEED - INC)
            else:
                print("Equal")
                if CORRECTION:
                    gopigo.set_left_speed(SPEED)
                    gopigo.set_right_speed(SPEED)

            print(time.time() - t)
    except Exception, e:
        print(e)
except KeyboardInterrupt:
    pass
gopigo.stop()
