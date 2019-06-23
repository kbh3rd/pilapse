#!/usr/bin/env python

# :set ts=4 sw=4 expandtab
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
#------------------------------------------------------------------------


################################################################################
# -- submenu class; each instance is one set of related selections
################################################################################

class submenu :

    VERSION = "$Revision: 1.4 $ $Date: 2019/06/23 18:12:57 $"

    def __init__ (self, name) :

        self.name = name
        self.selection = -1
        self.prompts = []
        self.values  = []
        self.count = 0


    def additem (self, prompt, value, selected) :

        # -- Add an item to a menu and return its index

        self.prompts.append(prompt)
        self.values.append(value)
        self.count = len(self.values)
        if selected  or self.selection < 0 :
            self.selection = self.count - 1
        return (self.count - 1)

    def setval (self, valix) :

        # -- set selection index

        if valix >= 0  and  valix < self.count :
            self.selection = valix
            return valix
        else :
            return -1

    def value (self) :

        # -- return the value of the current selection

        if self.count <= 0 :
            return
        if self.selection < 0 or self.selection >= self.count :
            self.selection = 0
        return self.values[self.selection]

    def current (self) :

        #-- return display prompt and value of the current selection 

        if self.count <= 0 :
            return "", ""
        else :
            return self.prompts[self.selection], self.values[self.selection]

    def selnext (self) :

        # -- Increment the selection and return new prompt & value

        if self.count <= 0 :
            return "", ""
        else :
            self.selection += 1
            if self.selection >= self.count :
                self.selection = 0
            return self.prompts[self.selection], self.values[self.selection]

    def whichat (self, which) :

        # -- return prompt and value at the given index modulo set size

        if self.count <= 0 :
            return "", ""
        which = which % self.count
        return self.prompts[which], self.values[which]
        

if __name__ == "__main__" :

    ################################################################################
    # -- Initialize menu set
    ################################################################################


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
    modes.additem ('Frames', 'F', 0)
    modes.additem ('Video', 'V', 1)

    # ---------------------------------
    # -- Frames per Second

    fps = submenu ("FPS")
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


    #-- The set that comprises the whole menu system

    menus = [resolutions, modes, fps, reclen, cycle]



    ################################################################################
    # -- Exercise the menus
    ################################################################################

    print cycle.VERSION+"\n"

    for menu in menus :
        print menu.name
        for ix in range (0, menu.count) :
            prompt, val = menu.whichat (ix)
            print "\t", prompt,
            if ix == menu.selection :
                print "*"
            else :
                print


    print "\nCycle FPS:\n"

    for ix in range (0, fps.count) :
        prompt, val = fps.selnext()
        print prompt

    print "\nCurrent Values:\n"

    print "--------------------------------"
    for menu in menus :
        prompt, value = menu.current()
        print "%s: %s" % (menu.name, prompt)
    print "--------------------------------"
        
    print "\nIncrement reclen\n"

    prompt, value = reclen.selnext()
    print prompt

    print "\nreclen prompts\n"
    print reclen.prompts
