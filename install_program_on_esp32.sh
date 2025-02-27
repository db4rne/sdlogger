#!/bin/sh

python ~/hacks/micropython/tools/mpremote/mpremote.py connect /dev/ttyACM0 mip install sdcard
python ~/hacks/micropython/tools/mpremote/mpremote.py connect /dev/ttyACM0 mip install requests
python ~/hacks/micropython/tools/mpremote/mpremote.py connect /dev/ttyACM0 mip install github:mkomon/uota

python ~/hacks/micropython/tools/mpremote/mpremote.py connect /dev/ttyACM0 fs cp main.py :main.py
python ~/hacks/micropython/tools/mpremote/mpremote.py connect /dev/ttyACM0 fs cp uota.cfg :uota.cfg
python ~/hacks/micropython/tools/mpremote/mpremote.py connect /dev/ttyACM0 fs cp version :version

python ~/hacks/micropython/tools/mpremote/mpremote.py connect /dev/ttyACM0 soft-reset

