#!/bin/sh


if [ -z "$1" ]
then
	echo "no argument found, first argument should be version number, e.g.: ./create_firmware_update.sh 3.43.23"
	exit 1
fi

tar -czf firmware_update/firmware.tar.gz main.py
checksum=$(sha256sum firmware_update/firmware.tar.gz | cut -d ' ' -f 1)

# write new line into firmware_update/latest file
# example line:
# 2.0.1;firmware.tar.gz;0;8870f8b3bd8b54437f0a7f721cd3f3fe208e60638dcf36a9f4efe31dab58c548
echo "$1;firmware.tar.gz;0;$checksum" >> firmware_update/latest

echo "new latest file:"
cat firmware_update/latest


