# SPDX-License-Identifier: GPL-2.0-or-later



BUFSIZE_BUFFER = const(49 * 1024)
BUFSIZE_RXBUF = const(32 * 1024)
BUF_THRESHOLD = const(16 * 1024)
UART_TIMEOUT = const(1000) # timeout to start writing in ms
# buffer is very big chunk of memory, therefore we allocate it as early as possible
BUFFER = bytearray(BUFSIZE_BUFFER)

import os, vfs
import time
import json
import gc

from machine import UART
from machine import SPI
from machine import Pin
from machine import RTC
from machine import WDT
from machine import reset
from sdcard import SDCard

DEBUG = True
# set True for debug output

BUF_POS = 0
SD_MOUNT = '/sd'
LOG_FOLDER = 'logs'
OLD_LOG_FOLDER = 'old_logs'
LOG_FILENAME = 'logfile.log'
LOG_PATH = SD_MOUNT + '/' + LOG_FOLDER + '/' + LOG_FILENAME
CMD_PREFIX = const(b"__sdlogger__ {")
BUF_LASTLINE = bytearray(1024)
BUF_POS_LASTLINE = 0
WRITETIME = time.ticks_ms()
# access token for demo server
URL_ACCESS_TOKEN = 'Ti0TahcaiN0Ahkeb1eegaiv6gu'

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
RTC0 = RTC()


def debug(text):
    global DEBUG
    if DEBUG == True:
        print("DEBUG: " + text)

def sdcard_init():
    """sdcard setup, mounting and creating logfile and folder"""
    os.mount(SD, SD_MOUNT)
    dirls = os.listdir(SD_MOUNT)
    if not LOG_FOLDER in dirls:
        os.mkdir(SD_MOUNT + '/' + LOG_FOLDER)
    if not OLD_LOG_FOLDER in dirls:
        os.mkdir(SD_MOUNT + '/' + OLD_LOG_FOLDER)
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
    global DEBUG
    fd = open(LOG_PATH, "ab")
    mv = memoryview(BUFFER)
    fd.write(mv[:BUF_POS])
    fd.flush()
    fd.close()
    debug("SD write: " + str(BUF_POS) + " bytes")
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
    # linux kernel sends \r\n on line end
    global BUF_POS
    global BUF_POS_LASTLINE
    global BUF_LASTLINE
    global BUFFER

    debug("parse_cmd start")

    debug("BUF_POS: " + str(BUF_POS))
    firstnl = BUFFER.find(b'\r\n', 0, BUF_POS)
    debug("firstnl: " + str(firstnl))

    # if firstnl == -1: line not complete (yet)
    # append whole line to BUF_LASTLINE
    # add bytes written to BUF_POS_LASTLINE
    if firstnl == -1:
        # write part of line into BUF_LASTLINE
        buf_line_len = BUF_POS_LASTLINE + BUF_POS
        BUF_LASTLINE[BUF_POS_LASTLINE:buf_line_len] = BUFFER[0:BUF_POS]
        BUF_POS_LASTLINE = buf_line_len
        return

    # found a newline, will append it to BUF_LASTLINE and check for command
    if (firstnl != -1) and (firstnl + BUF_POS_LASTLINE) < len(BUF_LASTLINE):
        buf_line_len = BUF_POS_LASTLINE + firstnl
        BUF_LASTLINE[BUF_POS_LASTLINE:buf_line_len] = BUFFER[0:firstnl]
        cmd = BUF_LASTLINE.find(CMD_PREFIX, 0, buf_line_len)
        # found command in BUF_LASTLINE
        if (cmd != -1):
            json_start = cmd + len(CMD_PREFIX) - 1
            mv = memoryview(BUF_LASTLINE)
            exec_cmd(mv[json_start:buf_line_len])

    lastnl = BUFFER.rfind(b'\r\n', firstnl, BUF_POS)
    debug("lastnl: " + str(lastnl))
    # found last newline, will copy into BUF_LASTLINE from lastnl till BUF_POS
    # update BUF_POS_LASTLINE
    # this is always the start of a BUF_LASTLINE, therefore implicis reset of BUF_POS_LASTLINE
    if lastnl > 0:
        t = BUF_POS - (lastnl + 2)
        debug("t: " + str(t))
        BUF_LASTLINE[0:t] = BUFFER[lastnl:BUF_POS]
        BUF_POS_LASTLINE = t
    # check for command between firstnl and lastnl
    cmd_pos = firstnl
    while True:
        cmd_pos = BUFFER.find(CMD_PREFIX, cmd_pos, lastnl)
        if cmd_pos == -1:
            break
        else:
            line_end = BUFFER.find(b'\r', cmd_pos, lastnl)
            cmd_pos = cmd_pos + len(CMD_PREFIX) - 1
            mv = memoryview(BUFFER)
            exec_cmd(mv[cmd_pos:line_end])


def exec_cmd(json_cmd):
    try:
        cmd  = json.loads(json_cmd)
    except Exception:
        return
    debug("command found: " + cmd['cmd'])
    if cmd['cmd'] == "RTC":
        exec_rtc(cmd)
    elif cmd['cmd'] == "upload":
        exec_upload(cmd)
    elif cmd['cmd'] == "UOTA":
        exec_uota(cmd)
    elif cmd['cmd'] == "reset":
        exec_reset(cmd)

def exec_rtc(cmd):
    global RTC0
    # the command should have an option "epoch", giving seconds since year 1970
    # micropython uses epoch based in 2000, so 946684800 seconds later
    RTC0.datetime(time.gmtime(cmd['epoch'] - 946684800))
    debug(str(RTC0.datetime()))

def exec_reset(cmd):
    reset()

def network_connect(cmd):
    if 'wlan_password' in cmd:
        pass 
    else:
        cmd['wlan_password'] = None
    # connect to WLAN
    debug("connecting to ssid " + str(cmd['wlan_ssid']) + " password: " + str(cmd['wlan_password']))
    import network
    wlan = network.WLAN(network.WLAN.IF_STA)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(cmd['wlan_ssid'], cmd['wlan_password'])
        while not wlan.isconnected():
            pass
    debug("wlan connected")

def prepare_lowmem():
    global BUFFER
    del BUFFER # delete buffer to free some memory for upload process
    global UART0
    UART0.deinit()
    del UART0
    gc.collect()

def setup_wdt(seconds):
    from machine import WDT
    wdt = WDT(timeout = seconds * 1000)

def exec_upload(cmd):
    # options:
    # wlan_ssid
    # wlan_password - optional
    # upload_server
    # router_mac - MACaddress of the router
    global URL_ACCESS_TOKEN
    global LOG_FOLDER
    global OLD_LOG_FOLDER
    prepare_lowmem()
    debug(f"free memory before network connect: {gc.mem_free()}")
    setup_wdt(1200)
    network_connect(cmd)
    # upload file to server
    import requests
    logpath = SD_MOUNT + '/' + LOG_FOLDER
    old_logpath = SD_MOUNT + '/' + OLD_LOG_FOLDER
    ls = os.listdir(logpath)
    debug("files to upload: " + str(ls))
    for file in ls:
        gc.collect()
        response = requests.request("POST", cmd['upload_server'] + '/' + cmd['router_mac'] + file, data=sd_read_chunks(logpath + '/' + file), timeout=60, headers={"Access-Token": URL_ACCESS_TOKEN})
        debug(f"HTTP status code: {response.status_code}")
        if response.status_code == 200:
            # move uploaded file to OLD_LOG_FOLDER
            os.rename(logpath + '/' + file, old_logpath + '/' + file)
            pass
    # hard reset
    reset()

def sd_read_chunks(file):
    fd = open(file, "rb")
    buf = bytearray(512)
    mv = memoryview(buf)
    while True:
        gc.collect()
        debug(f"gc.mem_free: {gc.mem_free()}")
        length = fd.readinto(mv)
        debug(f"read {length} bytes {fd.tell()}, garbage: {gc.mem_free()}")
        yield mv[0:length - 1]
        if length < len(buf):
            break
    fd.close()
    debug("read file " + str(file) + " from SD")

def exec_uota(cmd):
    # options:
    # wlan_ssid
    # wlan_password - optional
    prepare_lowmem()
    setup_wdt(3600)
    import uota
    network_connect(cmd)
    if uota.check_for_updates():
        uota.install_new_firmware()
    reset()

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
    debug("SD initialized, entering control loop")
    while True:
        control()


if not DEBUG:
    try:
        main()
    except Exception:
        # dont catch e.g. KeyboardInterrupt or SystemExit
        reset()
else:
    main()

