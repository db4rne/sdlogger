# SPDX-License-Identifier: GPL-2.0-or-later

BUFSIZE_BUFFER = const(49 * 1024)
BUFSIZE_RXBUF = const(32 * 1024)
BUF_THRESHOLD = const(16 * 1024)
UART_TIMEOUT = const(1000) # timeout to start writing in ms
BUFFER = bytearray(BUFSIZE_BUFFER)

import os, vfs
import time
import json

from machine import UART
from machine import SPI
from machine import Pin
from machine import RTC
from sdcard import SDCard

BUF_POS = 0
SD_MOUNT = '/sd'
LOG_FOLDER = 'logs'
LOG_FILENAME = 'logfile.log'
LOG_PATH = SD_MOUNT + '/' + LOG_FOLDER + '/' + LOG_FILENAME
CMD_PREFIX = const(b"sdlogger {")
BUF_LASTLINE = bytearray(1024)
BUF_POS_LASTLINE = 0
WRITETIME = time.ticks_ms()

UART0 = UART(0, baudrate=115200, rx=20, tx=21, rxbuf=BUFSIZE_RXBUF)
SDSPI = SPI(1,
            baudrate=1320000, # will be overwritten by sdcard.py
            polarity=0,
            phase=0,
            bits=8,
            firstbit=SPI.MSB,
            sck=Pin(6),
            mosi=Pin(2),
            miso=Pin(4))
SD = SDCard(SDSPI, Pin(9, Pin.OUT))


def sdcard_init():
    """sdcard setup, mounting and creating logfile and folder"""
    os.mount(SD, SD_MOUNT)
    dirls = os.listdir(SD_MOUNT)
    if not LOG_FOLDER in dirls:
        os.mkdir(SD_MOUNT + '/' + LOG_FOLDER)
    # find the new filename for LOG_FILENAME. eg: foo.log23
    dirls = os.listdir(SD_MOUNT + '/' + LOG_FOLDER)
    x = -1
    for file in dirls:
        tmpstr = ''.join(filter(str.isdigit, file))
        if tmpstr:
            tmp = int(tmpstr)
            if tmp > x :
                x = tmp
    global LOG_FILENAME
    global LOG_PATH
    LOG_FILENAME = LOG_FILENAME + str(x+1)
    LOG_PATH = SD_MOUNT + '/' + LOG_FOLDER + '/' + LOG_FILENAME

def writebuf():
    """ write buffer to SDcard """
    global BUF_POS
    global WRITETIME
    global LOG_PATH
    dbg_tmr = time.ticks_ms()
    fd = open(LOG_PATH, "ab")
    mv = memoryview(BUFFER)
    fd.write(mv[:BUF_POS])
    fd.flush()
    fd.close()
    diff_tmr = time.ticks_diff(time.ticks_ms(), dbg_tmr)
    print(f"SD write time: {diff_tmr} ms for {BUF_POS} bytes")
    BUF_POS = 0
    WRITETIME = time.ticks_ms()


def readuart():
    mv = memoryview(BUFFER)
    global BUF_POS
    global BUFSIZE_RXBUF
    global BUFSIZE_BUFFER
    if (BUF_POS + BUFSIZE_RXBUF) < (BUFSIZE_BUFFER - 1024):
        num = UART0.readinto(mv[BUF_POS : BUF_POS + BUFSIZE_RXBUF])
    else:
        num = UART0.readinto(mv[BUF_POS : BUFSIZE_BUFFER - 1024])
    BUF_POS = BUF_POS + num
    if (num >= BUFSIZE_RXBUF) or (BUF_POS >= BUFSIZE_BUFFER - 1024):
        tmp = str.encode("\r\nsdlogger: buffer was full\r\n")
        mv[BUF_POS:BUF_POS+len(tmp)] = tmp

def parse_cmd():
    # find first \n
    # expand BUF_LASTLINE
    # check for CMD_PREFIX
    # 
    # find last newline
    # search for CMD_PREFIX between first and last newline
    #
    # lastline = from last newline
    global BUF_POS
    global BUF_POS_LASTLINE
    global BUF_LASTLINE
    global BUFFER

    firstnl = BUFFER.find(b'\r', 0, BUF_POS)
    if (firstnl != -1) and ((firstnl + BUF_POS_LASTLINE) < len(BUF_LASTLINE)):
        buf_line_len = BUF_POS_LASTLINE + firstnl
        BUF_LASTLINE[BUF_POS_LASTLINE:buf_line_len] = BUFFER[0:firstnl]
        cmd = BUF_LASTLINE.find(CMD_PREFIX, 0, buf_line_len)
        if (cmd != -1):
            json_start = cmd + len(CMD_PREFIX) - 1
            mv = memoryview(BUF_LASTLINE)
            exec_cmd(mv[json_start:buf_line_len])

    lastnl = BUFFER.rfind(b'\r', BUF_POS)
    t = BUF_POS - lastnl
    BUF_LASTLINE[0:t] = BUFFER[lastnl:BUF_POS]
    cmd  = 0
    while cmd != -1:
        cmd = BUFFER.find(CMD_PREFIX, firstnl, lastnl)
        if cmd != -1:
            line_end = BUFFER.find(b'\r', cmd, lastnl)
            json_start = cmd + len(CMD_PREFIX) - 1
            mv = memoryview(BUFFER)
            exec_cmd(mv[json_start:line_end])


def exec_cmd(json_cmd):
    try:
        cmd  = json.loads(json_cmd)
    except:
        return
    if cmd['cmd'] == "rtc":
        exec_rtc(cmd)
    elif cmd['cmd'] == "upload":
        exec_upload(cmd)
    elif cmd['cmd'] == "reset":
        exec_reset(cmd)

def exec_rtc(cmd):
    rtc  = machine.RTC()
    # the command should have an option "epoch", giving seconds since year 2000
    rtc.datetime(time.gmtime(cmd['epoch']))

def exec_reset(cmd):
    import machine
    machine.reset()

def exec_upload(cmd):
    # options:
    # wlan_ssid
    # wlan_password - optional
    # upload_server
    global BUFFER
    del BUFFER # delete buffer to free some memory for upload process
    if 'wlan_password' in cmd:
        pass 
    else:
        cmd['wlan_password'] = None
    import network
    wlan = network.WLAN(network.WLAN.IF_STA)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(cmd['wlan_ssid'], cmd['wlan_password'])
        while not wlan.isconnected():
            pass
    # TODO: upload file to server


def control():
    """main control loop"""
    if UART0.any():
        # read UART if any characters available
        readuart()
    if (BUF_POS > BUF_THRESHOLD) or (BUF_POS > 0 and (1000 < time.ticks_diff(time.ticks_ms(), WRITETIME))):
        # write log if no UART transfer for more than WRITETIME seconds or buffer is fuller than BUF_THRESHOLD
        parse_cmd()
        writebuf()

def main():
    sdcard_init()
    while True:
        control()

main()

