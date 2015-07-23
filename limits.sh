#!/bin/bash                                                                                                                                                                                                                                                                                                                                                               

sudo launchctl limit maxfiles 8096 8096
sudo launchctl limit maxproc 8096 8096

ulimit -n 8096
ulimit -u 1024
