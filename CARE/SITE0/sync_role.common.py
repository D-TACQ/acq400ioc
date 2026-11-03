#!/bin/sh
# sync_role.common
# set.site 0 sync_role fpmaster|rpmaster|master|solo|slave FS FIN [opts]
import subprocess
import sys
from pathlib import Path

roles = {}
acq1014_roles = {}


def fpmaster():
    set_common()
    set_out()
    set_common_master()
    set_site(0, "SYS:CLK:FPMUX", "FPCLK")
    set_site(0, "SIG:SRC:TRG:0", "EXT")
    set_master(FS, FIN)


def rpmaster():
    set_common()
    set_out()
    set_slave(0)
    set_common_master()
    set_site(0, "SIG:SRC:TRG:0", "HDMI")
    set_site(0, "SYS:CLK:FPMUX", "ZCLK")
    set_site(0, "SIG:ZCLK_SRC", "CLK.d0")
    set_master(FS, FIN)


def master():
    set_common()
    set_out()
    D_TRG = "d1"
    set_common_master()
    set_local_clock(FS)
    if is_48x():
        set_48x_override(FS, master)


def solo():
    set_common()
    set_local_clock(FS)


def slave():
    set_common()
    set_out_slave()
    set_slave()
    if is_48x():
        set_48x_override(FS, slave)
    if is_43x():
        set_43x_override(FS, slave)


def slavemb():
    set_common()
    set_out_slave()
    set_slave(0)
    set_site(0, "SIG:ZCLK_SRC", "CLK.d0")
    set_site(0, "SYS:CLK:FPMUX", "ZCLK")
    set_site(0, "SIG:CLK_MB:FIN", FIN)
    set_mb(FS)
    set_site(0, "SIG:SRC:CLK:1" "MCLK")


def acq1014_master_solo():
    if not TRG:
        TRG = "int"
    D_TRG = "d1"
    set_common()
    subprocess.run(["/usr/local/bin/acq1014_select_clk_src", "int", FS, FIN_CLKSTAR])


def acq1014_fpmaster():
    set_common()
    if acq1014_clk_src != 2:
        print("ERROR: RPCLK has priority")
        return 1
    else:
        subprocess.run(["/usr/local/bin/acq1014_select_clk_src", "ext", FS, FIN])


def acq1014_rpmaster():
    set_common()
    if acq1014_clk_src != 2:
        print("ERROR: RP CABLE NOT CONNECTED")
        return 1
    else:
        subprocess.run(["/usr/local/bin/acq1014_select_clk_src", "ext", FS, FIN])


def acq1014_slave():
    set_common()
    # Be careful with FIN. For slaves this is 20MHz for
    # rear panel masters this will be 1MHz.
    fin = FIN_CLKSTAR
    if "x$P3" != "x":
        fin = FIN
    subprocess.run(["/usr/local/bin/acq1014_select_clk_src", "ext", FS, fin])


roles["fpmaster"] = fpmaster
roles["rpmaster"] = rpmaster
roles["master"] = master
roles["solo"] = solo
roles["slave"] = slave
roles["slavemb"] = slavemb

acq1014_roles["master"] = acq1014_master_solo
acq1014_roles["solo"] = acq1014_master_solo
acq1014_roles["fpmaster"] = acq1014_fpmaster
acq1014_roles["rpmaster"] = acq1014_rpmaster
acq1014_roles["slave"] = acq1014_slave


def set_mbclk():
    fs = f"{dollar1}"
    if fs < FMIN:
        # ensure a valid fs, ignore any user CLKDIV
        clkdiv = 5 * FMIN / fs
        CLKDIV = clkdiv
        fs = CLKDIV * fs
        set_site(S1, "CLKDIV", CLKDIV)
    else:
        # assert CLKDIV, possibly user
        set_site(S1, "CLKDIV", CLKDIV)
    set_site(0, "SIG:CLK_MB:SET", fs)


set_mb = set_mbclk


def select_lo_zclk():
    set_site(0, "SYS:CLK:FPMUX" "ZCLK")
    set_site(0, "SIG:ZCLK_SRC" "INT33M")
    set_site(0, "SIG:CLK_MB:FIN" "33333000")


def select_lo_xclk():
    set_site(0, "SYS:CLK:FPMUX", "XCLK")
    set_site(0, "SIG:CLK_MB:FIN", "32768000")


select_lo = select_lo_zclk


def set_acq43x_sample_rate():
    set_site(S1, "ACQ43X_SAMPLE_RATE", dollar1)


def sync_trg_to_clk():
    if SYNC_TRG_TO_CLK.exists():
        set_site(S1, "sync_trg_to_clk", dollar1)


def set_slave_acq1001():
    set_site(0, "SYS:CLK:FPMUX", "OFF")
    sync_trg_to_clk(0)
    set_site(0, "SIG:SRC:CLK:${1:-1}", "HDMI")
    set_site(0, "SIG:SRC:TRG:0", "HDMI")
    set_site(0, "SIG:SRC:SYNC:0", "HDMI")
    set_site(S1, f"clk=1,d1,{CLK_SENSE}")
    set_site(S1, f"trg=1,d0,{TRG_SENSE}")
    if "x$ROLE" == "x${ROLE#*master}":
        if SYNC.exists():
            set_site(S1, "sync=1,d0,rising")
    set_site(S1, "CLKDIV", f"{CLKDIV:-1}")


def set_slave_acq2106():
    set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", 0)
    set_slave_acq1001(dollar1)


def set_common_master_acq1001():
    set_site(0, "SIG:SRC:CLK:1", "MCLK")
    sync_trg_to_clk(1)
    if ACQ43X_SAMPLE_RATE.exists():
        pass
    else:
        set_site(S1, "CLKDIV", f"{CLKDIV:-1}")
    if SYNC.exists():  # /etc/acq400/$S1/sync:
        set_site(S1, "sync=0,0,0")


def set_common_master_acq2106():
    set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", "1")
    set_site(0, "SYS:CLK:BYPASS", "0")
    set_common_master_acq1001()


def is_48x(mez):
    if "ACQ48" in mez:
        return True
    else:
        return False


def is_42x(mez):
    if "ACQ42" in mez:
        return True
    elif "AO42" in mez:
        return True
    else:
        return False


def is_43x(mez):
    if "ACQ43" in mez:
        return True
    else:
        return False


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
    set_sys("/dev/acq400.0.knobs/mod_en", "1")


def set_out_slave():
    set_site(0, "SIG:SYNC_OUT:CLK", "CLK")
    set_site(0, "SIG:SYNC_OUT:CLK:DX", "d1")
    set_site(0, "SIG:SYNC_OUT:TRG", "TRG")
    set_site(0, "SIG:SYNC_OUT:TRG:DX", "d0")
    set_site(0, "SIG:SYNC_OUT:SYNC", "SYNC")
    set_site(0, "SIG:SYNC_OUT:SYNC:DX", "d0")
    set.sys("/dev/acq400.0.knobs/mod_en", "1")


def set_48x_override():
    # Configure clock
    if not CLKDIV:
        CLKDIV = 1
    if f"{dollar2}" == "master":
        if is_acq2106 != 0:
            # Configure clock - This is NOT valid for FPCLK
            set_site(0, "SIG:SRC:CLK:0", "INT01M")
            fin = 1000000
        else:
            zclk_src = INT33M
        fin = 33333000
    else:
        set_site(0, "SIG:SRC:CLK:0", "HDMI")
        fin = f"{FIN}"

    if not zclk_src:
        zclk_src = "CLK.d0"
    set_site(0, "SYS:CLK:FPMUX", "ZCLK")
    set_site(0, "SIG:ZCLK_SRC", f"{zclk_src}")
    set_site(0, "SIG:CLK_MB:FIN", fin)
    set_mb(f"{dollar1}")
    set_site(0, "SIG:SRC:CLK:1", "MCLK")
    if is_acq2106() != 0:
        set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", "1")
    set_site(S1, "CLKDIV" "${CLKDIV}")
    # Configure HDMI Clock out
    set_site(0, "SIG:SYNC_OUT:CLK:DX", "d0")


def set_43x_override():
    hi_res_mode = 1
    if dollar1 >= 52000:
        hi_res_mode = 0
    set_site(S1, "hi_res_mode" f"{hi_res_mode}")


def config_distributor_sites():
    distributor_sites = get_site("0", distributor)
    # | awk '{ print dollar2 }' |
    # awk -F= '{ print dollar2 }' |
    # sed "s/,/ /g")

    if not CLKDIV:
        CLKDIV = 1

    if distributor_sites == "none":
        return 0

    for site in distributor_sites:
        if get_site("site", module_role) == "MASTER":
            set_site(site, "clk", "1,1,1")
            set_site(site, "trg=1,${TRG_DX:-dollar1},${TRG_SENSE:-rising}")
            set_site(site, "clkdiv", f"{CLKDIV}")
            set_site(site, "CLKDIV", f"{CLKDIV}")


# common to all
# report init status - this will be overwritten on successful completion
def set_common():
    DEV_SHM_ROLE.write_text("WARNING:$CMDLINE incomplete")


# 		set_site(0 SIG:*:RESET=1	&


def caput(pv, value):
    subprocess.run(["caput", "-t", pv, value, ">/dev/null"])


def pv_read_lock():
    caput(f"{PV_BASE}:1:{dollar1}:r.DISA", f"{dollar2}")


def set_local_clock():
    select_lo()
    set_mb(f"{dollar1}")
    pv_read_lock(CLK, 1)
    set_site(S1, "clk=1,${CLK_DX:-d1},${CLK_SENSE}")
    pv_read_lock(CLK, 0)
    pv_read_lock(TRG, 1)
    set_site(S1, "trg=1,${TRG_DX:-d1},${TRG_SENSE}")
    pv_read_lock(TRG, 0)


def set_master():
    pv_read_lock(CLK, 1)
    set_site(S1, "clk=1,${CLK_DX:-d1}", f"{CLK_SENSE}")
    pv_read_lock(CLK, 0)
    pv_read_lock(TRG, 1)
    set_site(S1, "trg=1,${TRG_DX:-d0}", f"{TRG_SENSE}")
    pv_read_lock(TRG, 0)
    set_site(0, "SIG:CLK_MB:FIN", f"{dollar2}")
    set_mb(f"{dollar1}")


def parse_args(args):
    px = 1
    for token in args:
        if "=" in token:
            key, val = token.split("=", 1)
            if key == "TRG:SENSE":
                config["TRG_SENSE"] = val
            elif key == "CLK:SENSE":
                config["CLK:SENSE"] = val
            elif key == "TRG":
                # int or ext, pick dX defaults for most boxes
                config["TRG"] = val
                if val == "int":
                    config["TRG_DX"] = "d1"
                elif val == "ext":
                    config["TRG_DX"] = "d0"
            elif key == "TRG:DX":
                config["TRG_DX"] = val  # not previously defined. actual dX line..
            elif key == "CLK:DX":
                config["CLK_DX"] = val
            elif key == "CLKDIV":
                config["CLKDIV"] = val
            else:
                print(f"error {key} not defined", file=sys.stderr)
        else:
            # positional argument (no "=" present)
            px = len(config["positionals"]) + 1
            if px <= 3:
                config["positionals"].append(token)
            else:
                print(f"error discard parameter {px} {token}", file=sys.stderr)
    return config


def get_site(site_number: int, site_parameter: str):
    return subprocess.run(["get.site", site_number, site_parameter])


def set_site(site_number: int, site_parameter: str, site_parameter_value: str):
    return subprocess.run(
        ["set.site", site_number, site_parameter, site_parameter_value]
    )


def set_sys(sys_param_path: str, sys_param_value: str):
    return subprocess.run(["set.sys", sys_param_path, sys_param_value])


DEV_SHM_ROLE = Path("/dev/shm/role")
RUN0_LOG = Path("/etc/acq400/0/run0_log")
ACQ43X_SAMPLE_RATE = Path("/etc/acq400/$S1/ACQ43X_SAMPLE_RATE")
SYNC_TRG_TO_CLK = Path("/etc/acq400/$S1/sync_trg_to_clk")
SYNC = Path(f"/etc/acq400/{S1}/sync")
TRG = None
TRG_SENSE = "rising"
CLK_SENSE = "rising"
FMIN = 4000000
CLKDIV = 1
FIN_DEF = 1000000
FIN_CLKSTAR = 20000000
P1 = None
P2 = None
P3 = None


def main():
    if sys.argv[1] == "":
        if DEV_SHM_ROLE.exists():
            print(DEV_SHM_ROLE.read_text())
        else:
            print("role not set")
        return 0
    elif sys.argv[1] == "help":
        print(
            "USAGE sync_role {fpmaster|rpmaster|master|slave|slavemb|solo} [CLKHZ] [FIN]"
        )
        print("modifiers [CLK|TRG:SENSE=falling|rising] [CLK|TRG:DX=d0|d1]")
        print("modifiers [TRG=int|ext]")
        print("modifiers [CLKDIV=div]")
        sys.exit(0)

    # echo busy > /dev/shm/role
    DEV_SHM_ROLE.write_text("busy")

    CMDLINE = "$*"

    s1 = None
    if RUN0_LOG.exists():
        fields = []
        for line in RUN0_LOG.read_text().splitlines():
            parts = line.replace("," " ").split()
            if len(parts) >= 2:
                fields.append(parts[1])
        s1 = "\n".join(fields)
    # hmm default is zero, not helpful, if no XI, we need a dummy aggregator
    # we could say if $s1 == 0 then go look at the distributor to find distributor s1?
    # THIS WAS ALL SO MUCH SIMPLER when we ALWAYS populated from SITE1!

    if s1:
        S1 = s1
    else:
        S1 = 1

    # TODO: insert the below line back in
    # set_site($S1 CLK=1 2>&1 > /dev/null

    if ACQ43X_SAMPLE_RATE.exists():
        select_lo = select_lo_xclk
        set_mb = set_acq43x_sample_rate

    MOD = get_site("0", "MODEL")
    MEZ = get_site(S1, "MODEL")

    CLKDX_OUT = d1

    if MOD[0:7] in ["acq2106", "acq2206", "acq1102"]:
        set_slave = set_slave_acq2106
        set_common_master = set_common_master_acq2106
        # Si5326 minimum output rate. 2M works for slave XO hardware
        FMIN = 10000
        is_acq2106 = 1
    else:
        set_slave = set_slave_acq1001
        set_common_master = set_common_master_acq1001
        # ics527 minimum output rate
        FMIN = 4000000
        # avoid local clkdiv on slow SLAVE SAR devices
        if is_42x():
            CLKDX_OUT = d2
        is_acq2106 = 0

    FS_DEF = 200000
    if is_48x():
        FS_DEF = 20000000

    # PV readback on triplet en,dx,edge can cause errors, so lock it
    # source /etc/profile.d/epics.sh
    # TODO: implement the above sourcing in python
    PV_BASE = f"{IOC_HOST}"

    # execution here...
    ROLE = f"{P1}"
    if not P2:
        P2 = f"{FS_DEF}"
    if not P3:
        P3 = f"{FIN_DEF}"
    subprocess.run(["egu2int", f"FS={P2}", f"FIN={P3}"])

    D_TRG = "d0"

    try:
        if MOD[0:7] == "acq1014":
            if not TRG:
                TRG = "ext"
            acq1014_clk_src = get_site("2", acq1014_clk)
            rc = acq1014_roles[ROLE]()
            if rc > 0:
                print("ERROR: role dollar1 not valid")
                return 1
            # Set the trigger dependent on role or TRG= override on command line
            # Assume post mode. TRG_DX is ignored for ACQ1014
            subprocess.run(
                [
                    "/usr/local/bin/acq1014_select_trg_src",
                    f"{TRG}",
                    "post",
                    f"{TRG_SENSE}",
                ]
            )
        else:
            roles[ROLE]()
    except Exception as e:
        print(f"ERROR: role dollar1 not valid: {e}")
        return 1

    def executable(s):
        # check if its executable
        pass

    def execute(s):
        # execute the file
        pass

    if executable("/etc/acq400/0/on_sync_role"):
        execute("/etc/acq400/0/on_sync_role")
    # Configure distributor (XO) after AI.
    config_distributor_sites(f"{D_TRG}")

    with open("/dev/shm/role", "w") as f:
        f.writeline(f"{CMDLINE}")
    with open("/dev/shm/role_fs_hz", "w") as f:
        f.writeline(f"{FS}")
    return 0


if __name__ == "__main__":
    main()
