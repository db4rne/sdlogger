#! /usr/bin/python

BUFSIZE_BUFFER = const(49 * 1024)
BUFSIZE_RXBUF = const(32 * 1024)
BUF_THRESHOLD = const(16 * 1024)
UART_TIMEOUT = const(1000) # timeout to start writing in ms
BUFFER = bytearray(BUFSIZE_BUFFER)

import os, vfs
import time

from machine import UART
from machine import SPI
from machine import Pin
from sdcard import SDCard

BUF_POS = 0
SD_MOUNT = '/sd'
LOG_FOLDER = 'logs'
LOG_FILENAME = 'logfile.log'
LOG_PATH = SD_MOUNT + '/' + LOG_FOLDER + '/' + LOG_FILENAME
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


def control():
    """main control loop"""
    if UART0.any():
        # read UART if any characters available
        readuart()
    if (BUF_POS > BUF_THRESHOLD) or (BUF_POS > 0 and (1000 < time.ticks_diff(time.ticks_ms(), WRITETIME))):
        # write log if no UART transfer for more than WRITETIME seconds or buffer is fuller than BUF_THRESHOLD
        writebuf()

def main():
    sdcard_init()
    while True:
        control()

main()

