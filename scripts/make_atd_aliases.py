#!/usr/bin/env python3

"""
Generates aliases for analogue trigger

Usage:
    ./make_atd_aliases.py > /mnt/local/sysconfig/st_pre_atd-aliases.cmd
"""

import os

def run_main():
    hostname, atd_sites = get_atd_sites()

    for site in atd_sites:
        nchan = int(cmd(f"cat /etc/acq400/{site}/NCHAN"))
        for chan in range(1, nchan + 1):
            idk = "" if chan <= 16 else "2"
            bit = f"B{(chan-1)%16:x}".upper()
            print(f"alias( {hostname}:{site}:ANATRG:SRC{idk}.{bit}, {hostname}:{site}:ANATRG:LIVE:CH{chan:02} )")
            print(f"alias( {hostname}:{site}:ANATRG:GROUP_MASK{idk}.{bit}, {hostname}:{site}:ANATRG:GROUP:CH{chan:02} )")

def get_atd_sites():
    atd_sites = []
    hn = None
    for pv in os.popen("grep ANATRG:GROUP_SRC$ /tmp/records.dbl").read().split("\n"):
        fields = pv.split(':')
        if len(fields) > 2:
            atd_sites.append(fields[1])
            hn = fields[0]
    return hn, atd_sites

def cmd(cmd):
    return os.popen(cmd).read()

if __name__ == '__main__':
    run_main()
