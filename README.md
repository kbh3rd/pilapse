# pilapse

This is the Python code for the Raspberry Pi Zero W time-lapse camera
described at https://egb13.net/time-lapse-pi-camera.  The hardware features
of the camera that this code needs to interface with are:

* A Standard original Pi camera module
* 3 buttons
* 1 zero-to-nine number wheel read on 4 GPIO inputs as binary digits
* 1 32x2 character monochrome LCD display
* 1 LED

The software modules are:

pilapse.sh:

	Run from /etc/rc.local at boot time.  It launches the Python
	code that manages the camera and the user interface, and then
	reading and acting on directives and file names from the stdout
	of the Python code.

pilapse.py:

	The core of the system, managing the hardware and the user interface


submenu.py:

	Class for the items in a menu for the user interface.  The full menu
	is a list of submenus.
