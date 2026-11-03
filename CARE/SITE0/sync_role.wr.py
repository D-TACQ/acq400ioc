# sync_role.wr
# set.site 0 sync_role fpmaster|rpmaster|master|solo|slave FS [FMB] [opts] 

#set -x 
import logging
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

"""
ROLE=$P1

FIN=$(egu2int ${FIN_DEF})
"""

def mad_wr_func():
    if SITE=$S1 is_ds:
        FS_DEF = 40000
        if P2:
            FS = egu2int(P2)
        else:
            FS = egu2int(FS_DEF)
        set_site($S1 ACQ43X_SAMPLE_RATE 0
        if FS == 10000:
            FMB_DEF=5M12
            hrmode=1
        elif FS == 20000:
            FMB_DEF=10M24
            hrmode=1    	
        elif FS == 40000:
            FMB_DEF=20M48
            hrmode=1 
        elif FS == 80000:
            FMB_DEF=20M48
            hrmode=0
        elif FS == 125000:
            FMB_DEF=32M
            hrmode=0
        elif FS == 128000:
            FMB_DEF=32M768
            hrmode=0
        else:
            print("ERROR: SR options 10k 20k 40k 80k 125k 128k")
            sys.exit(1)
        esac
        set_site($S1  hi_res_mode $hrmode
    else:
        CLKDIV=unknown
        if is_tiga():
            FMB_DEF = 10M
            FS_DEF = 200000
            if P2:
                FS = P2
            else:
                FS = FS_DEF
            if FS == FMB_DEF:
                CLKDIV=1
        else:
            FMB_DEF = 40M
            FS_DEF = 20M
            if is_48x():
                FS_DEF = 20M
        if P2:
            FS = P2
        else:
            FS = FS_DEF
        if FS > 100:
            FS = str(FS/10000000)+"0M"
            if FS == FMB_DEF:
                CLKDIV=1
            else:
                plan = in_the_plan(FS)
                if plan != FMB_DEF:
                    FMB_DEF = plan
                    CLKDIV = 1
        else:
            CLKDIV="unknown"

        if CLKDIV == "unknown":	
            if P2:
                FS = egu2int(P2)
            else:
                FS = egu2int(FS_DEF)
            FMB = egu2int(FMB_DEF)
            CLKDIV = FMB / FS
            FS= FMB / CLKDIV
            print(f"calculated {CLKDIV}")

def parse_args(args):
    config = {}
    px=1
    for token in args:
        if "=" in token:
            key, val = token.split("=", 1)
            if key == "TRG:SENSE":
                config["TRG:SENSE"] = val
            elif if key == "CLK:SENSE":
                config["CLK_SENSE"] = val
            elif key == "TRG":
                config["TRG"] = val  # int or ext, pick dX defaults for most boxes
                if val == "int":
                    config["TRG_DX"] = d1
                elif val == "ext":
                    config["TRG_DX"] = d0
            elif key == "TRG:DX":
                config["TRG_DX"] = val  # not previously defined. actual dX line.
            elif key == "CLK:DX":
                config["CLK_DX"] = val
            elif key == "CLKDIV":
                config["CLKDIV"] = val
            else:
                print(f"error {key} not defined", file=sys.stderr)
        else:
            config["positionals"] = sys.argv[1:]
            px = len(config["positionals"]) + 1
            if px <= 3:
                config["positionals"].append(token)
            else:
                print(f"error discard parameter {px} {token}")
    return config

def sync_trg_to_clk(val):
    if exists /etc/acq400/$S1/sync_trg_to_clk:
        set_site(S1, "sync_trg_to_clk", val)

get_site(S1, MODEL)

def is_48x():
    return "ACQ48" in get_site(S1, MODEL)

def is_42x():
    return "ACQ42\" in get_site(S1, MODEL) or "AO42" in get_site(S1, MODEL)

def set_slave_acq1001():
    set_site(0, "SYS:CLK:FPMUX OFF")
    sync_trg_to_clk(0)
    set_site(0, "SIG:SRC:CLK:${1:-1}, "HDMI")
    set_site(0, "SIG:SRC:TRG:0", "HDMI")
    set_site(0, "SIG:SRC:SYNC:0", "HDMI")
    set_site(S1, "clk=1,d1,${CLK_SENSE}")
    set_site(S1, "trg=1,d0,${TRG_SENSE}")
    [ "x$ROLE" = "x${ROLE#*master}" ] && set_site(S1, "sync=1,d0,rising")
    set_site(S1, CLKDIV=${CLKDIV:-1})


def set_slave_acq2106():
    set_site(0 SYS:CLK:OE_CLK1_ZYNQ 0
    set_slave_acq1001 $1

def set_common_master_acq1001():
    set_site(0 SIG:SRC:CLK:1 MCLK
    sync_trg_to_clk 1
    [ -e /etc/acq400/$S1/ACQ43X_SAMPLE_RATE ] || set_site($S1 CLKDIV=${CLKDIV:-1}
    set_site($S1 "sync=0,0,0"

def set_common_master_acq2106() {
    set_site(0 SYS:CLK:OE_CLK1_ZYNQ 1
    set_site(0 SYS:CLK:BYPASS 0
    set_common_master_acq1001
}
# common to all
# report init status - this will be overwritten on successful completion
def set_common():
    echo "WARNING:$CMDLINE incomplete" > /dev/shm/role
#    set_site(0 SIG:*:RESET=1  &

# even a slave can master another link in the chain..
# we share the MB clock and the SITE trigger 
# The MASTER syncs the SITE trigger, SLAVES MUST leave it untouched.
def set_out():
    set_site(0, "SIG:SYNC_OUT:CLK", "CLK")
    set_site(0, "SIG:SYNC_OUT:CLK:DX", f"{CLKDX_OUT}")
    set_site(0, "SIG:SYNC_OUT:TRG", "TRG")
    set_site(0, "SIG:SYNC_OUT:TRG:DX", "d2")
    set_site(0, "SIG:SYNC_OUT:SYNC", "SYNC")
    set_site(0, "SIG:SYNC_OUT:SYNC:DX", "d2")


def set_out_slave():
    set_site(0, "SIG:SYNC_OUT:CLK", "CLK")
    set_site(0, "SIG:SYNC_OUT:CLK:DX", "d1")
    set_site(0, "SIG:SYNC_OUT:TRG", "TRG")
    set_site(0, "SIG:SYNC_OUT:TRG:DX", "d0")
    set_site(0, "SIG:SYNC_OUT:SYNC", "SYNC")
    set_site(0, "SIG:SYNC_OUT:SYNC:DX", "d0")

def config_distributor_sites():
	distributor_sites=get_site(0, "distributor")
    # TODO: include the awking seds
    # | awk '{ print $2 }' | awk -F= '{ print $2 }' | sed "s/,/ /g")
    if distributor_sites == "none":
        return 0
	
    for site in distributor_sites:
        if get_site(site, "module_role") == "MASTER":
			set_site(site, "clk", '1,1,1')
			set_site(site, "CLKDIV=${CLKDIV:-1}")
			set_site(site, "trg=1,${TRG_DX:-$1},${TRG_SENSE:-rising}")

def pv_read_lock(pv, val):
    caput -t $PV_BASE:1:$1:r.DISA $2 >/dev/null

def set_local_clock():
    pv_read_lock("CLK", "1")
    set_site($S1 "clk=1,${CLK_DX:-d1},${CLK_SENSE}")
    pv_read_lock("CLK", "0")
    pv_read_lock("TRG", "1")
    set_site($S1 "trg=1,${TRG_DX:-d1},${TRG_SENSE}")
    pv_read_lock("TRG", "0")


# execution here... FMB must match a valid load file eg 20M

def in_the_plan(plan):
    PLANS="$(for file in /etc/si5326.d/si5326_31M25*txt; do fs=${file#*_31M25-}; echo ${fs%*.txt}; done)";
    for pl in PLANS:
        if plan == pl:
            print(pl)
            return 0
    print(FMB_DEF)

def wr():
    set_local_clock()
    set_common()
    set_out()
    D_TRG='d1'
    set_common_master()
    MOD=$(get.site 0 MODEL)
    if MOD == "acq1102":
    	/usr/local/CARE/acq1102+WR.init ${FMB_DEF} ${CLKDIV}
    else:
    	/usr/local/CARE/acq2106+WR.init ${FMB_DEF} ${CLKDIV}
    /usr/local/CARE/route-WR-FP    1>&2
    if exists /etc/acq400/0/on_sync_role:
        /etc/acq400/0/on_sync_role
    # Configure distributor (XO) after AI.
    config_distributor_sites $D_TRG
    echo "$CMDLINE ;# FIN=$FIN FMB_DEF=$FMB_DEF FIN_DEF=$FIN_DEF" > /dev/shm/role
    echo $FS > /dev/shm/role_fs_hz;;
    return 0

TRG=None
TRG_SENSE=rising
CLK_SENSE=rising

CMDLINE="$*"
CLKDIV=1

P1=None
P2=None
P3=None
# always with WR:
FIN_DEF=31M25
D_TRG='d0'

RUN0_LOG = Path("/etc/acq400/0/run0_log")

def main():
    roles["wr"] = wr
    roles["fpmaster"] = wr
    roles["rpmaster"] = wr
    roles["master"] = wr
    roles["solo"] = wr
    roles["slave"] = wr
    roles["whiterabbit"] = wr

    MOD = get_site(0, "MODEL")
    if MOD[0:7] == "acq2106":
        set_slave=set_slave_acq2106
        set_common_master=set_common_master_acq2106
    set_site(S1, "CLK=1") #2>&1 > /dev/null

    CLKDX_OUT="d1"

    # PV readback on triplet en,dx,edge can cause errors, so lock it
    source /etc/profile.d/epics.sh
    PV_BASE=${IOC_HOST}

    s1 = None
    if RUN0_LOG.exists():
        fields = []
        for line in RUN0_LOG.read_text().splitlines():
            parts = line.replace(",", " ").split()
            if len(parts) >= 2:
                fields.append(parts[1])
        s1 = "\n".join(fields)
    if s1:
        S1 = s1
    else:
        S1 = 1

    arg1 = sys.argv[1]

    if arg1 == "": 
        if exists /dev/shm/role
            cat /dev/shm/role
        else:
            print("role not set")
        sys.exit(0)
    elif arg1 == "help":
        print("USAGE sync_role {wr|whiterabbit|fpmaster|rpmaster|master|slave|solo} [CLKHZ] [FIN]")
        print("modifiers [CLK|TRG:SENSE=falling|rising] [CLK|TRG:DX=d0|d1]")
        print("modifiers [TRG=int|ext]")
        print("modifiers [CLKDIV=div]")
        sys.exit(0)

    try:
        roles[ROLE]()
    except:
        print("ERROR: role $1 not valid")
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
