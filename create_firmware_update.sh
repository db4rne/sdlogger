#!/bin/sh

FILELIST="main.py uota.cfg version requests.py"

tar -czf firmware_update/firmware.tar.gz ${FILELIST}
CHECKSUM=$(sha256sum firmware_update/firmware.tar.gz | cut -d ' ' -f 1)
VER=$(tr -d '\r' < version)

# write new line into firmware_update/latest file
# example line:
# 2.0.1;firmware.tar.gz;0;8870f8b3bd8b54437f0a7f721cd3f3fe208e60638dcf36a9f4efe31dab58c548
echo "${VER};firmware.tar.gz;0;${CHECKSUM}" > firmware_update/latest

echo "new latest file:"
cat firmware_update/latest


