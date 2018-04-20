import gopigo
import sys
import time

LEFT = 0
RIGHT = 1

SPEED = int(sys.argv[1])
INC = 15

SAFE_DISTANCE = 35
USS = 15

TRIM = int(sys.argv[2])
CORRECTION = sys.argv[3] == "true"
print(CORRECTION)

# Might as well try this out, probably doesn't do anything though
gopigo.disable_encoders()
gopigo.enable_encoders()

gopigo.trim_write(TRIM)

time.sleep(0.1)
initial_ticks_left = gopigo.enc_read(LEFT)
time.sleep(0.1)
initial_ticks_right = gopigo.enc_read(RIGHT)

elapsed_ticks_left = 0
elapsed_ticks_right = 0

try:
    try:
        gopigo.set_speed(SPEED)
        gopigo.fwd()
        while True:
            dist = gopigo.us_dist(USS)
            print("Dist: " + str(dist))
            if dist < SAFE_DISTANCE:
		break

            #time.sleep(0.1)
            elapsed_ticks_left = gopigo.enc_read(LEFT) - initial_ticks_left
            #time.sleep(0.1)
            elapsed_ticks_right = gopigo.enc_read(RIGHT) - initial_ticks_right

            print("L: " + str(elapsed_ticks_left) + "\tR: " + str(elapsed_ticks_right))

            if elapsed_ticks_left > elapsed_ticks_right:
                print("RIGHT SLOW")
                if CORRECTION:
                    gopigo.set_left_speed(SPEED - INC)
                    gopigo.set_right_speed(SPEED + INC)
            if elapsed_ticks_left < elapsed_ticks_right:
                print("LEFT SLOW")
                if CORRECTION:
                    gopigo.set_left_speed(SPEED + INC)
                    gopigo.set_right_speed(SPEED - INC)
    except Exception, e:
        print(e)
except KeyboardInterrupt:
    pass
gopigo.stop()
