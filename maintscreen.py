import subprocess

import pygame
import webcolors

import config
import toucharea
from config import debugprint, WAITNORMALBUTTON
from utilities import interval_str

wc = webcolors.name_to_rgb
from logsupport import Error
import time
import sys
from utilities import scaleW, scaleH


class MaintScreenDesc:
    def __init__(self):
        debugprint(config.dbgscreenbuild, "Build Maintenance Screen")

        self.CharColor = "white"
        self.BackgroundColor = "royalblue"
        self.DimTO = 100000  # infinite
        self.ExtraCmdKeys = []

        self.PrevScreenKey = None
        self.NextScreenKay = None
        self.ExtraCmdKeys = []

        self.name = "Maint"
        self.label = ["Maintenance"]

        maintkeys = ('log', 'exit', 'shut', 'restart', 'shutpi', 'reboot')
        mainttitles = (
        'Show Log', 'Exit Maintenance', 'Shutdown Console', 'Restart Console', 'Shutdown Pi', 'Reboot Pi')
        self.menukeysbyord = []
        self.keysbyord = []
        t = config.topborder + scaleH(100)  # todo pixel
        keyheight = (config.screenheight - t - config.topborder)/len(
            maintkeys)  # todo move to better layout solution if more keys needed
        # note: using topborder in above line rather than bottomborder because we don't have to leave space for cmd keys
        for i in range(len(maintkeys)):
            self.menukeysbyord.append(toucharea.ManualKeyDesc(maintkeys[i], [mainttitles[i]], (config.screenwidth/2, t),
                                                              (config.screenwidth - 2*config.horizborder, keyheight),
                                                              'gold',
                                                              'black', 'black', 'black', 'black'))
            t += keyheight

        self.pagekeysbyord = [toucharea.TouchPoint((config.screenwidth/2, config.screenheight/2),
                                                   (config.screenwidth, config.screenheight))]

    def ShowScreen(self):

        config.screen.fill(wc(self.BackgroundColor))
        r = config.fonts.Font(scaleH(40), '', True, True).render("Console Maintenance", 0,
                                                                 wc(self.CharColor))  # todo pixel
        rl = (config.screenwidth - r.get_width())/2
        config.screen.blit(r, (rl, config.topborder))
        r = config.fonts.Font(scaleH(25), '', True, True).render("Up: " + interval_str(time.time() - config.starttime),
                                                                 0,
                                                                 wc(self.CharColor))  # todo pixel
        rl = (config.screenwidth - r.get_width())/2
        config.screen.blit(r, (rl, config.topborder + scaleH(30)))  # todo pixel
        for K in self.keysbyord:
            config.DS.draw_button(config.screen, K)
        pygame.display.update()

    def HandleScreen(self, newscr=True):
        config.toDaemon.put([])
        # stop any watching for device stream
        self.keysbyord = self.menukeysbyord
        Logs = config.Logs
        Logs.Log("Entering Maint Screen")
        self.ShowScreen()

        while 1:
            choice = config.DS.NewWaitPress(self)
            if choice[0] == WAITNORMALBUTTON:
                K = self.keysbyord[choice[1]]
                if K.name == 'exit':
                    return config.HomeScreen
                elif K.name == 'log':
                    item = 0
                    self.keysbyord = self.pagekeysbyord  # make whole screen single invisible key
                    while item >= 0:
                        item = Logs.RenderLog(self.BackgroundColor, start=item)
                        temp = config.DS.NewWaitPress(self)
                    self.keysbyord = self.menukeysbyord
                    self.ShowScreen()
                elif K.name == 'shut':
                    self.Exit_Options("Manual Shutdown Requested", "Shutting Down")
                    sys.exit()
                elif K.name == 'restart':
                    self.Exit_Options("Console Restart Requested", "Restarting")
                    z = 'nohup /bin/bash -c \" echo c1 > /home/pi/c1 && sleep 3 && echo c2 > /home/pi/c2 && python -u ' + \
                        sys.argv[0] + ' ' + config.configfile + '\"'
                    print z
                    subprocess.Popen(z, shell=True)
                    sys.exit()
                elif K.name == 'shutpi':
                    self.Exit_Options("Shutdown Pi Requested", "Shutting Down Pi")
                    subprocess.Popen('sudo shutdown -P now', shell=True)
                    sys.exit()
                elif K.name == 'reboot':
                    self.Exit_Options("Reboot Pi Requested", "Rebooting Pi")
                    subprocess.Popen('sudo reboot', shell=True)
                    sys.exit()
                else:
                    Logs.Log("Internal Error", Error)

            else:
                return choice[1]

    def Exit_Options(self, msg, scrnmsg):
        config.screen.fill(wc("red"))
        r = config.fonts.Font(40, '', True, True).render(scrnmsg, 0, wc("white"))
        config.screen.blit(r, ((config.screenwidth - r.get_width())/2, config.screenheight*.4))
        config.Logs.Log(msg)
        pygame.display.update()
        time.sleep(2)