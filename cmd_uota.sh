#!/bin/sh

WLANSSID="$(uci get wireless.default_radio0.ssid)"
WLANENC="$(uci get wireless.default_radio0.encryption)"

COMMAND="__sdlogger__ {\"cmd\": \"UOTA\", \"wlan_ssid\": \"${WLANSSID}\", "

if [ "$WLANENC" != "none" ]; then
	WLANPASS="$(uci get wireless.default_radio0.key)"
	COMMAND="${COMMAND}\"wlan_password\": \"${WLANPASS}\""
fi

COMMAND="${COMMAND}}"
echo "${COMMAND}" > /dev/kmsg

