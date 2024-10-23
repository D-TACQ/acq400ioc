#!/usr/bin/env python3

"""
Generates aliases for analogue trigger

Usage:
    ./make_atd_aliases.py > /mnt/local/sysconfig/site-aliases.db
"""

import os

def run_main():
    hostname = os.uname().nodename
    agg = string_to_dict(cmd("get.site 0 aggregator"))

    for site in agg['sites'].split(','):
        nchan = int(cmd(f"get.site {site} NCHAN"))
        for chan in range(1, nchan + 1):
            idk = "" if chan <= 16 else "2"
            hex_val = f"B{get_cycled_value(chan) - 1:x}".upper()
            print(f"alias( {hostname}:{site}:ANATRG:SRC{idk}.{hex_val}, {hostname}:{site}:ANATRG:LIVE:CH{chan:02} )")
            print(f"alias( {hostname}:{site}:ANATRG:GROUP_MASK{idk}.{hex_val}, {hostname}:{site}:ANATRG:GROUP:CH{chan:02} )")

def cmd(cmd):
    return os.popen(cmd).read()

def string_to_dict(string):
    return {key: value for key, value in (item.split('=') for item in string.split())}

def get_cycled_value(n, max_value=16):
    return (n - 1) % max_value + 1

if __name__ == '__main__':
    run_main()