#!/bin/sh
# mounts a folder to /var/discourse and installs bash (required by
# Discourse launcher script)
#
# HOWTO:
#
# 1. `docker machine ssh default` into the VM
# 2. `mkdir /mnt/sda1/var/discourse`
# 3. put this script at /var/lib/boot2docker/bootlocal.sh (this file
#    will be persisted through reboots)
# 4. `chmod +x /var/lib/boot2docker/bootlocal.sh`
# 5. reboot VM
# 6. follow installation instructions for Discourse
#
# based on /etc/rc.d/vbox within the boot2docker image and
# https://docs.google.com/document/d/1i2lkCV9RPpckC8xRRb8yeGhj1Jebyha-5OHpFiiaTYg/pub
#
#
# Author: Florian Bender
# Updated: 2015-09-22
# License: MIT
#
# Copyright (c) 2015 Florian Bender <fb+git@quantumedia.de>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject
# to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR
# ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# abort on error
set -e

# mount options incl. setting user name/group
mountOptions='defaults,iocharset=utf8'
if grep -q '^docker:' /etc/passwd; then
	mountOptions="${mountOptions},uid=$(id -u docker),gid=$(id -g docker)"
fi

# try mounting "$source" at "$dir", but quietly clean up
# empty directories if it fails
try_mount_share() {
	dir="$1"
	source="$2"

	mkdir -p "$dir" 2>/dev/null
	# fix permissions
	if grep -q '^docker:' /etc/passwd; then
		chown -R $(id -u docker):$(id -g docker) "$dir"
	fi
	if ! mount -o "$mountOptions" "$source" "$dir" 2>/dev/null; then
		rmdir "$dir" 2>/dev/null || true
		while [ "$(dirname "$dir")" != "$dir" ]; do
			dir="$(dirname "$dir")"
			rmdir "$dir" 2>/dev/null || break
		done

		return 1
	fi

	return 0
}

# bfirsh gets all the credit for this hacky workaround :)
try_mount_share /var/discourse /mnt/sda1/var/discourse \
	|| true


# install bash (required by Discourse launcher script) and nano
sudo -u docker tce-load -wi bash nano
