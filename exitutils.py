import os
import subprocess
import sys
import time
import signal

import pygame

import config
from logsupport import ConsoleWarning, ConsoleError
import webcolors

wc = webcolors.name_to_rgb


def Exit(option, trigger, ecode):
	os.chdir(config.exdir)  # set cwd to be correct when dirs move underneath us so that scripts execute
	print "Signal daemon to term"
	os.kill(config.Daemon_pid, signal.SIGTERM)
	config.Ending = True
	print "join wait"
	config.DaemonProcess.join()
	print "join done"
	subprocess.Popen(
		'nohup sudo /bin/bash -e scripts/consoleexit ' + option + ' ' + config.configfile + ' ' + trigger + '>>../log.txt 2>&1',
		shell=True)
	sys.exit(ecode)

def dorealexit(K, YesKey, presstype):
	ExitKey = K.name
	if ExitKey == 'shut':
		Exit_Options("Manual Shutdown Requested", "Shutting Down")
	elif ExitKey == 'restart':
		Exit_Options("Console Restart Requested", "Restarting")
	elif ExitKey == 'shutpi':
		Exit_Options("Shutdown Pi Requested", "Shutting Down Pi")
	elif ExitKey == 'reboot':
		Exit_Options("Reboot Pi Requested", "Rebooting Pi")
	Exit(ExitKey, 'user', 0)

def errorexit(opt):
	if opt == 'restart':
		Exit_Options('Error restart', 'Error - Restarting')
	elif opt == 'reboot':
		consoleup = time.time() - config.starttime
		config.Logs.Log("Console was up: ", str(consoleup), severity=ConsoleWarning)
		print 'Up: ' + str(consoleup)
		if consoleup < 120:
			# never allow console to reboot the pi sooner than 120 seconds
			Exit_Options('Error Reboot Loop', 'Suppressed Reboot')
			opt = 'shut'  # just close the console - we are in a reboot loop
		else:
			Exit_Options('Error reboot', 'Error - Rebooting Pi')
	elif opt == 'shut':
		Exit_Options('Error Shutdown', 'Error Check Log')
	print 'Errorexit: ', opt
	Exit(opt, 'error', 1)

def Exit_Options(msg, scrnmsg):
	config.screen.fill(wc("red"))
	r = config.fonts.Font(40, '', True, True).render(scrnmsg, 0, wc("white"))
	config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.4))
	config.Logs.Log(msg)
	pygame.display.update()
	time.sleep(2)


def FatalError(msg):
	config.screen.fill(wc("red"))
	config.Logs.Log(msg, severity=ConsoleError)
	Exit('restart', 'codeerror', 99)
