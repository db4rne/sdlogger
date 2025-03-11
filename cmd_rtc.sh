#! /bin/sh

EPOCH=$(date +%s)

echo "__sdlogger__ {\"cmd\": \"RTC\", \"epoch\": ${EPOCH}}" > /dev/kmsg
