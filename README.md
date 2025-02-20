# SDLOGGER

sdlogger takes all data from uart0 rx and writes it onto a sdcard.



# available commands

- RTC
    - "epoch" : unix timestamp in seconds
- upload
    - wlan_ssid
    - wlan_password: optional, do not provide if open wlan is to be used
    - upload_server: server URL, e.g.: "http://localhost" port 80/443 will get autoassigned based on http or https
    - router_mac: mac address of the router, will be used in filename
- UOTA
    - wlan_ssid
    - wlan_password: optional, do not provide if open wlan is to be used
- reset
    - no options

## creating JSON for commands

```
#! /usr/bin/env python
import json

json.dumps({'cmd': 'RTC','epoch':123456778890})

```

