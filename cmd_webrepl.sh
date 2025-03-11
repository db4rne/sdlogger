#!/bin/sh

WLANSSID="$(uci get wireless.default_radio0.ssid)"
WLANENC="$(uci get wireless.default_radio0.encryption)"
WEBREPL_PASSWORD="1234" # at least 4 digits

COMMAND="__sdlogger__ {\"cmd\": \"webrepl\", \"wlan_ssid\": \"${WLANSSID}\""

if [ "$WLANENC" != "none" ]; then
	WLANPASS="$(uci get wireless.default_radio0.key)"
	COMMAND="${COMMAND}, \"wlan_password\": \"${WLANPASS}\""
fi

COMMAND="${COMMAND}, \"webrepl_pass\": ${WEBREPL_PASSWORD}}"
echo "${COMMAND}" > /dev/kmsg

