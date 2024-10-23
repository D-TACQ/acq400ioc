#!/usr/bin/env python3

"""
Generates aliases for analogue trigger

Usage:
    ./scripts/make_atd_aliases.py > /mnt/local/sysconfig/st_pre_atd-aliases.cmd
"""

import os

def run_main():
    hn, atd_sites = get_atd_sites()

    for site in atd_sites:
        nch = int(cmd(f"cat /etc/acq400/{site}/NCHAN"))
        for ch in range(1, nch + 1):
            idk = "" if ch <= 16 else "2"
            bit = f"B{(ch-1)%16:x}".upper()
            print(f"alias( {hn}:{site}:ANATRG:SRC{idk}.{bit}, {hn}:{site}:ANATRG:LIVE:CH{ch:02} )")
            print(f"alias( {hn}:{site}:ANATRG:GROUP_MASK{idk}.{bit}, {hn}:{site}:ANATRG:GROUP:CH{ch:02} )")

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
