#!/bin/bash

REPLACED_EMAIL="nii-rdmp@meatmail.jp"
TARGET_SUPPORT_EMAIL_LIST="
support@osf.io
support@osfio
"
TARGET_DIR_LIST="admin addons framework scripts tests website"


# protect
for dir in $(echo $TARGET_DIR_LIST); do
    if [ -d $dir ]; then
	:
    else
	echo "$dir: no such directory"
	exit 1
    fi
done

for email in $(echo $TARGET_SUPPORT_EMAIL_LIST); do
    grep -l -r --binary-files=without-match $email $TARGET_DIR_LIST | \
	xargs --no-run-if-empty sed -i -e "s/$email/$REPLACED_EMAIL/g"
done

# check
echo "These files are not updated:"
for email in $(echo $TARGET_SUPPORT_EMAIL_LIST); do
    grep -l -r --binary-files=without-match $email .
done
