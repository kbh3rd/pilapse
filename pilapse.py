#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

VERSION = "$Revision: 1.22 $"
VERDATE = "$Date: 2019/06/23 18:12:57 $"

#------------------------------------------------------------------------
# Copyright (c) 2019, EGB13.net
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The names of its contributors may not be used to endorse or promote
#       products derived from this software without specific prior
#       written permission.
# 
# THIS SOFTWARE IS PROVIDED ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
# THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#-------------------------------------------------------------------------------

from picamera import PiCamera
from datetime import datetime
import signal, os
import time
import sys

from submenu import submenu

import RPi.GPIO as GPIO
import Adafruit_GPIO.SPI as SPI
import Adafruit_CharLCD as LCD

#-- CONSTANTS ------------------------------------------------------------------

LAPSDIR = "/var/lapse"
FILEFMT = "image-%Y%m%dT%H%M%S.jpg"
PATHFMT = LAPSDIR + "/D%0.4d/%s"
HALTSPAN = 4    # hold duration for graceful shutdown
FLASHSEC = 0.20 # seconds to flash the led when taking a picture
SLEEPSEC = 0.05 # loop granularity

#- 16x2 character LCD pin configuration:

lcd_rs        = 25 #4
lcd_en        = 24 #18
lcd_d4        = 23 #17
lcd_d5        = 17 #27
lcd_d6        = 21 #22
lcd_d7        = 22 #5
lcd_backlight = 4       # ??
lcd_columns   = 16
lcd_rows      = 2

button1_pin   = 5

#- cool little 0-to-9 spinning button to select # seconds :-)
bcdpins = [26, 13, 19, 16]
bcdcode = [
            [1,1,1,1],  # 0
            [1,1,1,0],  # 1
            [1,1,0,1],  # 2
            [1,1,0,0],  # 3
            [1,0,1,1],  # 4
            [1,0,1,0],  # 5
            [1,0,0,1],  # 6
            [1,0,0,0],  # 7
            [0,1,1,1],  # 8
            [0,1,1,0]   # 9
]

ledpin = 14

#-- variables ------------------------------------------------------------------

maxct = 99
takepic = False
sperf   = 3   # seconds per frame default, but will read wheel

butpins     = [12, 5, 6]
butstate    = [0, 0, 0] # unpressed
butpress    = [0, 0, 0] # just pressed
butrele     = [0, 0, 0] # just released


#-- functions ------------------------------------------------------------------

def diskfree_str(path) :

    fbytes = diskfree(path)
    fkbytes = fbytes / 1024
    fmbytes = fkbytes / 1024
    fgbytes = fmbytes / 1024

    if fgbytes > 1 :
        return "%d G" % fgbytes
    if fmbytes > 1 :
        return "%d M" % fmbytes
    if fkbytes > 1 :
        return "%d K" % fkbytes
    return "%d B" % fbytes

# --

def diskfree (path) :
    
    dstat = os.statvfs(path)
    return dstat.f_bsize * dstat.f_bavail

# --

def filect (dir) :

    return len (os.listdir(dir) )

# --

def button_init () :

    GPIO.setmode(GPIO.BCM)
    for b in butpins :
        GPIO.setup(b, GPIO.IN)
    for b in bcdpins :
        GPIO.setup(b, GPIO.IN)

# --

def led_on () :
    GPIO.output (ledpin, 1)

def led_off () :
    GPIO.output (ledpin, 0)

def led_init () :
    GPIO.setup(ledpin, GPIO.OUT)
    led_off () ;

# --

def button_down (but) :

    # negative logic on buttons
    if but >= len(butpins) :
        return False
    bs = GPIO.input(butpins[but])
    if bs == False :
        return True
    else :
        return False

# --

def button_scan ():

    # track button state

    for bx in range (0, len(butpins) ) :
        bstate = button_down (bx)
        if bstate :
            if butstate[bx] == 0 :
                butpress[bx] = 1
            else :
                butpress[bx] = 0
            butrele[bx] = 0
        else :
            if butstate[bx] != 0 :
                butrele[bx] = 1
            else :
                butrele[bx] = 0
            butpress[bx] = 0
        butstate[bx] = bstate

# --

def button_press (but) :
    if but < len(butpins)  :
            return butpress[but]
    return 0

# --


# --

def button_release (but) :
    if but < len(butpins)  :
            return butrele[but]
    return 0

# --

def lcd_line (line, string) :

    s32 = "                                "
    if line < 0 or line > 2 :
            return
    lcd.set_cursor(0,(line - 1) )
    if len(string) < 32 :
        lcd.message (string+s32[len(string):])
    else :
        lcd.message (string[0:32])

# --

def lcd_2lines (l1, l2) :
    lcd_line (1, l1)
    lcd_line (2, l2)

# --

def lcd_space (lcd, state, dir, count) :

    if state :
        line1 = "# %d" % (count)
        line1 = line1[0:11]
        line1 = "%-11s%5s" % (line1, diskfree_str(LAPSDIR) ) 
        line2 = "D%0.4d %9ds" % (dir, sperf)
    else :
        stmsg = "OFF"
        line1 = "%16s" % (diskfree_str(LAPSDIR) )
        line2 = "%-9.9s%7s" % (resolutions.value(), "OFF")


    lcd_2lines (line1, line2)

# --

def read_sec () :

    bcd = [0,0,0,0]
    for bx in range(0,len(bcdpins)) :
        bs = GPIO.input(bcdpins[bx])
        bcd[bx] = bs

    for bx in range(0,len(bcdcode)) :
        if bcdcode[bx] == bcd :
            if (bx == 0) :
                return 10
            else :
                return bx

    return sperf # this oughtn't happen :-\

# --

def next_directory (startafter) :
    for num in range(startafter+1, 1000000) :
        dirpath = "%s/D%0.4d" % (LAPSDIR, num)
        try:
            os.mkdir(dirpath, 0777)
            return num
        except OSError:
            True

#-------------------------------------------------------------------------------

# -- initialize GPIO

button_init() 
led_init()

# -- initialize LCD

lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, 
               lcd_columns, lcd_rows, lcd_backlight)
lcd.enable_display(True)
lcd.clear()

# -- Init menu system

# ---------------------------------
# -- Resolution

resolutions = submenu ("Resolution")
resolutions.additem ('1920x1080 16:9', '1920x1080', 0)
resolutions.additem ('1280x720 16:9', '1280x720', 1)
resolutions.additem ('1640x922 16:9', '1640x922', 0)
resolutions.additem ('2592x1944 4:3', '2592x1944', 0)
resolutions.additem ('1296x972 4:3', '1296x972', 0)
resolutions.additem ('800x600 4:3', '800x600', 0)
resolutions.additem ('640x480 4:3', '640x480', 0)

# ---------------------------------
# -- Capture Mode

modes = submenu ("Mode")
modes.additem ('Frames only', 'F', 0)
modes.additem ('Video & frames', 'V', 1)

# ---------------------------------
# -- Frames per Second

fps = submenu ("FPS")
fps.additem ('6', 6, 0)
fps.additem ('12', 12, 0)
fps.additem ('18', 18, 0)
fps.additem ('24', 24, 1)
fps.additem ('30', 30, 0)

# ---------------------------------
# -- Recording Length in seconds

mn=60
hr=mn*60
dy=hr*24
mo=dy*30.5
yr=dy*365.25


reclen = submenu ("Recording length")
reclen.additem ('10 minutes', 10*mn, 0)
reclen.additem ('30 minutes', 30*mn, 0)
reclen.additem ('1 hour', hr, 0)
reclen.additem ('2 hours', 2*hr, 0)
reclen.additem ('3 hours', 3*hr, 0)
reclen.additem ('6 hours', 6*hr, 0)
reclen.additem ('12 hours', 12*hr, 0)
reclen.additem ('24 hours', 24*hr, 0)
reclen.additem ('forever', 12*yr, 1)    # 12 years feels like forever

# ---------------------------------
# -- Cycle reclen in new recordings

cycle = submenu ("Cycles")
cycle.additem ('Once', 0, 1)
cycle.additem ('Repeat', 1, 0)

# ---------------------------------
# -- ISO setting / auto every image

ISO = submenu ("ISO")
ISO.additem ('100', 100, 0)
ISO.additem ('200', 200, 0)
ISO.additem ('400', 400, 0)
ISO.additem ('800', 800, 0)
ISO.additem ('Auto', 0, 1)

#-- The set that comprises the whole menu system

menus = [resolutions, ISO, modes, fps, reclen, cycle]
menuix = 0
in_menu = False


# -----------------------------------------------------------------------------#
# -- MAIN ---------------------------------------------------------------------#
# -----------------------------------------------------------------------------#

sperf = read_sec()
sleepval = SLEEPSEC
picat = 0.0
dirnum = 0
framecount = 0

flashat = 0

b1start = 0
b2start = 0

camera = PiCamera()
lcd_2lines (VERSION, VERDATE)
time.sleep (1.5)
lcd_space(lcd, False, dirnum, 0)
shutter = camera.exposure_speed
gain = camera.awb_gains
camera.close()


try:

    while True :

        time.sleep (sleepval)
        loopstart = time.time() # for timing how long all this takes
        button_scan()

        # button 0
        if button_press(0) :
            if in_menu == False :
                # toggle picture taking
                sys.stderr.write("0 pressed\n")
                takepic = not takepic
                if (takepic) :
                    sys.stderr.write("On\n")
                    dirnum = next_directory(dirnum)
                    sperf = read_sec()
                    framecount = 0
                    lcd_space(lcd, takepic, dirnum, framecount)
                    picat = loopstart + sperf
                    camera = PiCamera()
                    if ISO.value() != 0 :
                        camera.iso = ISO.value()
                    #camera.resolution = "720p"
                    camera.resolution = resolutions.value()
                    camera.rotation = 270
                    if modes.value() == 'V' :
                        flag = "#VIDEO vidpath=%s/VIDEO/lapse-%0.4d.mp4 fps=%d\n" % (LAPSDIR, dirnum, fps.value())
                    else :
                        flag = "#IMAGES\n"
                    sys.stdout.write(flag)
                else :
                    sys.stderr.write("Off\n")
                    sys.stdout.write("#END\n")
                    sys.stdout.flush()
                    camera.close()
                    takepic = False
                    framecount = 0
                    lcd_space(lcd, takepic, dirnum, framecount)
            else :
                in_menu = False
                lcd_space(lcd, takepic, dirnum, framecount)

        schas = time.time()
        if button_press(1) :
            b1start = schas
            if not takepic :
                if not in_menu :
                    in_menu = True
                    menuix = 0
                    lcd_2lines (" ", " ")
                else :
                    menuix = (menuix + 1) % len (menus)
                prompt, val = menus[menuix].current()
                lcd_line (1, menus[menuix].name)
                lcd_line (2, prompt)

        if button_press(2) :
            b2start = schas
            if in_menu :
                prompt, val = menus[menuix].selnext()
                lcd_line (2, prompt)

        # Buttons 1 & 2 extended hold to shut down gracefully
        if button_down(1) and button_down(2) :
            if ( (schas - b1start) >= HALTSPAN) and ( (schas - b2start) >= HALTSPAN) :
                # shutdown; may require running as root
                lcd.clear()
                lcd_line(1, "Shutting down")
                os.system("shutdown -h now")

                exit (0)

        # Is it time to turn off the led flash?
        if flashat > 0 :
            if loopstart >= flashat :
                led_off()
                flashat = 0


        # Is it time to take a picture yet?
        if (takepic) :
            if loopstart >= picat :
                schas = time.time()
                now = datetime.now()
                filename = now.strftime(FILEFMT)
                imgname = PATHFMT % (dirnum, filename)
                # sys.stderr.write(imgname+"\n")
                if framecount == 1 and ISO.value() != 0 :
                    #- get awb from cam and make it stay that way
                    shutter = camera.exposure_speed
                    camera.exposure_mode = 'off'
                    camera.shutter_speed = shutter
                    gain = camera.awb_gains
                    camera.awb_mode = 'off'
                    camera.awb_gains = gain
                camera.capture(imgname)

                sys.stdout.write(imgname+"\n")
                sys.stdout.flush()
                flashat = schas + FLASHSEC
                led_on()
                picat = loopstart + sperf
                framecount += 1

                camera.close()
                camera = PiCamera()
                camera.resolution = resolutions.value()
                camera.rotation = 270
                if ISO.value() != 0 :
                    #- restore initial values
                    camera.exposure_mode = 'off'
                    camera.awb_mode = 'off'
                    camera.iso = ISO.value()
                    camera.shutter_speed = shutter
                    camera.awb_gains = gain

            sperf = read_sec()
            lcd_space(lcd, takepic, dirnum, framecount)


        delta_t = (time.time() - loopstart)
        sleepval = SLEEPSEC - delta_t
        if (sleepval < 0) :
            sleepval = 0


# ------------------------------------------------------------------------------ 

except KeyboardInterrupt:
    lcd.clear()
    lcd.enable_display(False)
    GPIO.cleanup ()
    sys.stderr.write("\nexit\n")
    exit(1)
