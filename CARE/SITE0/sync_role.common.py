#!/usr/bin/python
"""
# sync_role.common
# set.site 0 sync_role fpmaster|rpmaster|master|solo|slave FS FIN [opts]
"""

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

# from typing import Callable

roles: dict[str, Callable] = {}
acq1014_roles: dict[str, Callable] = {}


@contextmanager
def simple_console_logger(name: str = "app", level: int = logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)

    try:
        yield logger
    finally:
        handler.close()
        logger.removeHandler(handler)


def source_shell_script(script_path, update_os_environ=True):
    path = Path(script_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"script not found at {path}")
    command = f"set -a && source '{path}' && env -0"

    result = subprocess.run(
        ["sh", "-c", command],
        env=os.environ.copy(),
        capture_output=True,
        text=False,
        check=True,
    )
    env_vars = {}
    for entry in result.stdout.decode("utf-8", errors="replace").split("\0"):
        if "=" in entry:
            key, val = entry.split("=", 1)
            env_vars[key] = val
    if update_os_environ:
        os.environ.update(env_vars)
    return env_vars


def fpmaster(S1):
    set_common()
    set_out()
    set_common_master(S1)
    set_site(0, "SYS:CLK:FPMUX", "FPCLK")
    set_site(0, "SIG:SRC:TRG:0", "EXT")
    set_master(S1)
    return 0


def rpmaster(S1):
    set_common()
    set_out()
    set_slave(0)
    set_common_master(S1)
    set_site(0, "SIG:SRC:TRG:0", "HDMI")
    set_site(0, "SYS:CLK:FPMUX", "ZCLK")
    set_site(0, "SIG:ZCLK_SRC", "CLK.d0")
    set_master(S1)
    return 0


def master(S1):
    set_common()
    set_out()
    trg.d_trg = "d1"
    set_common_master(S1)
    set_local_clock(S1)
    if is_48x(S1):
        set_48x_override(S1, "master")
    return 0


def solo(S1):
    set_common()
    set_local_clock(S1)
    return 0


def slave(S1):
    set_common()
    set_out_slave()
    set_slave(0)
    if is_48x(S1):
        set_48x_override(S1, "slave")
    if is_43x(S1):
        set_43x_override(S1, "slave")
    return 0


def slavemb(S1):
    set_common()
    set_out_slave()
    set_slave(0)
    set_site(0, "SIG:ZCLK_SRC", "CLK.d0")
    set_site(0, "SYS:CLK:FPMUX", "ZCLK")
    set_site(0, "SIG:CLK_MB:FIN", f"{freq.fin}")
    set_mb(S1)
    set_site(0, "SIG:SRC:CLK:1", "MCLK")
    return 0


def acq1014_master_solo(S1):
    if not trg.trg:
        trg.trg = "int"
    trg.d_trg = "d1"
    set_common()
    subprocess.run(
        [
            "/usr/local/bin/acq1014_select_clk_src",
            "int",
            f"{freq.fs}",
            f"{freq.fin_clkstar}",
        ],
        check=False,
    )
    return 0


def acq1014_fpmaster(S1):
    set_common()
    acq1014_clk_src = get_site("2", "acq1014_clk")
    if acq1014_clk_src != 2:
        print("ERROR: RPCLK has priority")
        return 1
    else:
        subprocess.run(
            [
                "/usr/local/bin/acq1014_select_clk_src",
                "ext",
                f"{freq.fs}",
                f"{freq.fin}",
            ],
            check=False,
        )
        return 0


def acq1014_rpmaster(S1):
    set_common()
    acq1014_clk_src = get_site("2", "acq1014_clk")
    if acq1014_clk_src != 2:
        print("ERROR: RP CABLE NOT CONNECTED")
        return 1
    else:
        subprocess.run(
            [
                "/usr/local/bin/acq1014_select_clk_src",
                "ext",
                f"{freq.fs}",
                f"{freq.fin}",
            ],
            check=False,
        )
        return 0


def acq1014_slave(S1):
    set_common()
    # Be careful with FIN. For slaves this is 20MHz for
    # rear panel masters this will be 1MHz.
    fin = freq.fin_clkstar
    if not inputs.P3:
        freq.fin = fin
    subprocess.run(
        ["/usr/local/bin/acq1014_select_clk_src", "ext", f"{freq.fs}", f"{fin}"],
        check=False,
    )
    return 0


def set_acq43x_sample_rate(sample_rate, S1):
    set_site(S1, "ACQ43X_SAMPLE_RATE", f"{sample_rate}")


def set_mbclk(S1):
    log.info(f"FS: {freq.fs} FIN: {freq.fin} {type(freq.fs)} {type(freq.fin)}")
    fs = int(freq.fs)
    fmin = freq.fmin
    if fs < fmin:
        # ensure a valid fs, ignore any user clk.clkdiv
        clkdiv = 5 * fmin / fs
        clk.clkdiv = clkdiv
        freq.fs = clk.clkdiv * fs
        # TODO: add a warning if we don't end up with an integer clock div
        clk.clkdiv_to_set = int(clk.clkdiv)
        set_site(S1, "clk.clkdiv", f"{clk.clkdiv_to_set}")
    else:
        # assert clk.clkdiv, possibly user
        set_site(S1, "clk.clkdiv", f"{clk.clkdiv}")
    set_site(0, "SIG:CLK_MB:SET", f"{fs}")


def select_lo_zclk():
    set_site(0, "SYS:CLK:FPMUX", "ZCLK")
    set_site(0, "SIG:ZCLK_SRC", "INT33M")
    set_site(0, "SIG:CLK_MB:FIN", "33333000")


def select_lo_xclk():
    set_site(0, "SYS:CLK:FPMUX", "XCLK")
    set_site(0, "SIG:CLK_MB:FIN", "32768000")


def sync_trg_to_clk(S1, n_clk):
    SYNC_TRG_TO_CLK = Path(f"/etc/acq400/{S1}/sync_trg_to_clk")
    if SYNC_TRG_TO_CLK.exists():
        set_site(S1, "sync_trg_to_clk", str(n_clk))


def set_slave(S1):
    """
    subsumed the below function into this one:

    def set_slave_acq2106(S1):
        set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", 0)
        set_slave_acq1001(S1, dollar1)

    """
    SYNC = Path(f"/etc/acq400/{S1}/sync")
    if is_acq2106():
        set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", 0)
    set_site(0, "SYS:CLK:FPMUX", "OFF")
    sync_trg_to_clk(S1, 0)
    set_site(0, "SIG:SRC:CLK:{S1}", "HDMI")
    set_site(0, "SIG:SRC:TRG:0", "HDMI")
    set_site(0, "SIG:SRC:SYNC:0", "HDMI")
    set_site(S1, f"clk=1,d1,{clk.clk_sense}")
    set_site(S1, f"trg=1,d0,{trg.trg_sense}")
    if "master" not in ROLE and SYNC.exists():
        set_site(S1, "sync=1,d0,rising")
    if not clk.clkdiv:
        clk.clkdiv = 1
    set_site(S1, "clk.clkdiv", f"{clk.clkdiv}")


def set_common_master(S1):
    """Sets common master for ACQ1001

    Subsumed below function into this one:

    def set_common_master_acq2106(S1):
        Sets common master for ACQ2106
        TODO: questionable whether this is required and we can't just branch logic in set_common_master_acq1001
        set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", "1")
        set_site(0, "SYS:CLK:BYPASS", "0")
        set_common_master_acq1001(S1)
    """
    ACQ43X_SAMPLE_RATE = Path(f"/etc/acq400/{S1}/ACQ43X_SAMPLE_RATE")
    SYNC = Path(f"/etc/acq400/{S1}/sync")

    if is_acq2106():
        set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", "1")
        set_site(0, "SYS:CLK:BYPASS", "0")
    set_site(0, "SIG:SRC:CLK:1", "MCLK")
    sync_trg_to_clk(S1, 1)
    if not clk.clkdiv:
        clk.clkdiv = 1
    if ACQ43X_SAMPLE_RATE.exists():
        pass
    else:
        set_site(S1, "clk.clkdiv", f"{clk.clkdiv}")
    if SYNC.exists():  # /etc/acq400/$S1/sync:
        set_site(S1, "sync=0,0,0")


def is_48x(S1):
    mez = get_site(S1, "MODEL")
    return "ACQ48" in mez


def is_42x(S1):
    mez = get_site(S1, "MODEL")
    return bool("ACQ42" in mez or "AO42" in mez)


def is_43x(S1):
    mez = get_site(S1, "MODEL")
    return "ACQ43" in mez


# even a slave can master another link in the chain..
# we share the MB clock and the SITE trigger
# The MASTER syncs the SITE trigger, SLAVES MUST leave it untouched.
def set_out():
    set_site(0, "SIG:SYNC_OUT:CLK", "CLK")
    set_site(0, "SIG:SYNC_OUT:CLK:DX", f"{clk.clkdx_out}")
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
    set_sys("/dev/acq400.0.knobs/mod_en", "1")


def set_48x_override(S1, master_or_slave: str):
    # Configure clock
    zclk_src = None
    if not clk.clkdiv:
        clk.clkdiv = 1
    if f"{master_or_slave}" == "master":
        if is_acq2106():
            # Configure clock - This is NOT valid for FPCLK
            set_site(0, "SIG:SRC:CLK:0", "INT01M")
            freq.fin = 1000000
        else:
            zclk_src = "INT33M"
        freq.fin = 33333000
    else:
        set_site(0, "SIG:SRC:CLK:0", "HDMI")
        freq.fin = freq.fin

    if not zclk_src:
        zclk_src = "CLK.d0"

    set_site(0, "SYS:CLK:FPMUX", "ZCLK")
    set_site(0, "SIG:ZCLK_SRC", f"{zclk_src}")
    set_site(0, "SIG:CLK_MB:FIN", f"{freq.fin}")
    set_mb(S1)
    set_site(0, "SIG:SRC:CLK:1", "MCLK")
    if is_acq2106():
        set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", "1")
    set_site(S1, f"CLKDIV={clk.clkdiv}")
    # Configure HDMI Clock out
    set_site(0, "SIG:SYNC_OUT:CLK:DX", "d0")
    return 0


def is_acq2106():
    ans = False
    MOD = get_site("0", "MODEL")
    if MOD[0:7] in ["acq2106", "acq2206", "acq1102"]:
        ans = True
    return ans


def set_43x_override(fs, master_or_slave, S1):
    hi_res_mode = 1
    if fs >= 52000:
        hi_res_mode = 0
    set_site(S1, f"hi_res_mode={hi_res_mode}")


def config_distributor_sites(distributor_trg):
    distributor_sites = get_site("0", "distributor")
    # | awk '{ print dollar2 }' |
    # awk -F= '{ print dollar2 }' |
    # sed "s/,/ /g")

    if not clk.clkdiv:
        clk.clkdiv = 1

    if distributor_sites == "none":
        return 0
    if not trg.trg_dx:
        trg.trg_dx = distributor_trg
    if not trg.trg_sense:
        trg.trg_sense = "rising"
    for site in distributor_sites:
        if get_site(site, "module_role") == "MASTER":
            set_site(site, "clk", "1,1,1")
            set_site(site, f"trg=1,{trg.trg_dx},{trg.trg_sense}")
            set_site(site, "clkdiv", f"{clk.clkdiv}")
            set_site(site, "CLKDIV", f"{clk.clkdiv}")


# common to all
# report init status - this will be overwritten on successful completion
def set_common():
    log.info("calling set_common")
    DEV_SHM_ROLE.write_text(f"WARNING: {CMDLINE} incomplete")


# 		set_site(0 SIG:*:RESET=1	&


def caput(pv, value):
    subprocess.run(["caput", "-t", pv, value, ">/dev/null"], check=False)


def pv_read_lock(pv: str, value):
    caput(f"{PV_BASE}:1:{pv}:r.DISA", f"{value}")


def set_local_clock(S1):
    select_lo()
    set_mb(S1)
    pv_read_lock("CLK", 1)
    if not clk.clk_dx:
        clk.clk_dx = "d1"
    if not trg.trg_dx:
        trg.trg_dx = "d1"
    set_site(S1, f"clk=1,{clk.clk_dx},{clk.clk_sense}")
    pv_read_lock("CLK", 0)
    pv_read_lock("TRG", 1)
    set_site(S1, f"trg=1,{trg.trg_dx},{trg.trg_sense}")
    pv_read_lock("TRG", 0)


def set_master(S1):
    pv_read_lock("CLK", 1)
    if not clk.clk_dx:
        clk.clk_dx = "d1"
    set_site(S1, f"clk=1,{clk.clk_dx},{clk.clk_sense}")
    pv_read_lock("CLK", 0)
    pv_read_lock("TRG", 1)
    if not trg.trg_dx:
        trg.trg_dx = "d0"
    set_site(S1, "trg=1,{trg.trg_dx}", f"{trg.trg_sense}")
    pv_read_lock("TRG", 0)
    set_site(0, "SIG:CLK_MB:FIN", f"{freq.fin}")
    set_mb(S1)


def parse_args(args):
    config = {"positionals": []}
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
                config["clk.clk_dx"] = val
            elif key == "clk.clkdiv":
                config["clk.clkdiv"] = val
            else:
                print(f"error {key} not defined", file=sys.stderr)
        else:
            if len(config["positionals"]) < 3:
                config["positionals"].append(token)
            else:
                print(f"error discard parameter {token}", file=sys.stderr)
    return config


def get_site(site_number: int, site_parameter: str):
    """returns the output string from get.site"""
    if isinstance(site_number, int):
        site_number_str = str(site_number)
    elif isinstance(site_number, str):
        site_number_str = site_number
    else:
        raise TypeError("Site number is not of correct type int or str")
    return subprocess.run(
        ["get.site", site_number_str, site_parameter],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def set_site(site_number: int, *site_params_vals):
    """returns the output string from set.site"""
    if len(site_params_vals) == 2:
        site_parameter, site_parameter_value = site_params_vals
    elif len(site_params_vals) == 1:
        if "=" not in site_params_vals[0]:
            raise ValueError("Two arg set_site requires PARAM=VALUE")
        site_parameter, site_parameter_value = site_params_vals[0].split("=", 1)

    log.info(f"set.site {site_number} {site_parameter} {site_parameter_value}")
    if isinstance(site_number, int):
        site_number_str: str = str(site_number)
    elif isinstance(site_number, str):
        site_number_str = site_number
    else:
        raise TypeError("Site number is not of corretc type str or int")
    return subprocess.run(
        ["set.site", site_number_str, site_parameter, site_parameter_value],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def set_sys(sys_param_path: str, sys_param_value: str):
    return subprocess.run(["set.sys", sys_param_path, sys_param_value], check=False)


def update_globals(args):
    log.info(args)
    if "TRG_DX" in args:
        trg.trg_dx = args["TRG_DX"]
    if "clk.clk_dx" in args:
        clk.clk_dx = args["clk.clk_dx"]
    return 0


def egu2int(x) -> int:
    log.info(f"egu2int called with input {x}")

    output = subprocess.run(
        ["/usr/local/bin/egu2int", f"{x}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    log.info(f"output of egu2int is {output}")
    try:
        log.info("trying to cast output to integer")
        int_output = int(output)
        log.info("great success")
        return int_output
    except Exception:
        log.info("failed casting output to integer")
        raise ValueError(f"egu2int cannot convert {x}")


DEV_SHM_ROLE = Path("/dev/shm/role")
RUN0_LOG = Path("/etc/acq400/0/run0_log")


@dataclass
class Clk:
    clk_sense: str = "rising"
    clkdiv: int = 1
    clkdx_out: str = "d1"
    clk_dx: str = ""


@dataclass
class Trg:
    trg: str = ""
    d_trg: str = "d0"
    trg_sense: str = "rising"
    trg_dx: str = ""


@dataclass
class Freq:
    fmin: int = 4000000
    fin_def: int = 1000000
    fin_clkstar: int = 20000000
    fin: int = -1
    fs: int = -1
    fs_def: int = 200000


@dataclass
class Inputs:
    P1: str = ""
    P2: str = ""
    P3: str = ""


# PV readback on triplet en,dx,edge can cause errors, so lock it
env_vars = source_shell_script("/etc/profile.d/epics.sh")
IOC_HOST = env_vars["IOC_HOST"]
# TODO: which env_vars are used in this script?
PV_BASE = f"{IOC_HOST}"

set_mb = set_mbclk
select_lo = select_lo_zclk

ROLE = None
CMDLINE = None

clk = Clk()
freq = Freq()
trg = Trg()
inputs = Inputs()


def main():
    global set_mb
    global select_lo
    global ROLE
    global CMDLINE
    log.info("starting sync_role.common.py")
    log.warning("starting sync_role.common.py")
    log.error("starting sync_role.common.py")

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

    # initial argument parsing
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
        print("modifiers [clk.clkdiv=div]")
        sys.exit(0)
    args = parse_args(sys.argv)
    print(args.keys())
    print(args["positionals"])
    inputs.P1 = args["positionals"][0]
    inputs.P2 = args["positionals"][1]
    inputs.P3 = args["positionals"][2]
    dollar1 = sys.argv[1]
    # echo busy > /dev/shm/role
    DEV_SHM_ROLE.write_text("busy")

    CMDLINE = " ".join(sys.argv[1:])

    update_globals(args)

    # checking run0 for sites
    s1 = None
    if RUN0_LOG.exists():
        fields = []
        for line in RUN0_LOG.read_text().splitlines():
            parts = line.replace(",", " ").split()
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

    set_site(S1, "CLK", "1")  # 2>&1 > /dev/null

    ACQ43X_SAMPLE_RATE = Path(f"/etc/acq400/{S1}/ACQ43X_SAMPLE_RATE")
    if ACQ43X_SAMPLE_RATE.exists():
        select_lo = select_lo_xclk
        set_mb = set_acq43x_sample_rate

    MOD = get_site("0", "MODEL")

    if is_acq2106():
        # Si5326 minimum output rate. 2M works for slave XO hardware
        freq.fmin = 10000
    else:
        # ics527 minimum output rate
        freq.fmin = 4000000
        # avoid local clkdiv on slow SLAVE SAR devices
        if is_42x(S1):
            clk.clkdx_out = "d2"

    if is_48x(S1):
        freq.fs_def = 20000000

    # execution here...
    ROLE = f"{inputs.P1}"
    log.info(f"ROLE: {ROLE}")

    if not inputs.P2:
        inputs.P2 = f"{freq.fs_def}"
    freq.fs = inputs.P2

    if not inputs.P3:
        inputs.P3 = f"{freq.fin_def}"
    freq.fin = inputs.P3

    freq.fs = egu2int(f"{inputs.P2}")
    freq.fin = egu2int(f"{inputs.P3}")

    try:
        if MOD[0:7] == "acq1014":
            if not trg.trg:
                trg.trg = "ext"
            rc = acq1014_roles[ROLE](S1)
            if rc > 0:
                print(f"ERROR: acq1014 role {dollar1} not valid")
                return 1
            # Set the trigger dependent on role or TRG= override on command line
            # Assume post mode. TRG_DX is ignored for ACQ1014
            subprocess.run(
                [
                    "/usr/local/bin/acq1014_select_trg_src",
                    f"{trg.trg}",
                    "post",
                    f"{trg.trg_sense}",
                ],
                check=False,
            )
        else:
            print(f"Not acq1014 and ROLE: {ROLE}")
            print(f"calling {roles[ROLE].__name__}()")
            rc = roles[ROLE](S1)
    except Exception as e:
        log.exception(f"Error: role {dollar1} not valid")
        print(f"ERROR: role {dollar1} not valid: {e}")
        return 1

    def executable(s):
        # check if it exists and is executable
        p = Path(s)
        return bool(p.exists())

    def execute(s):
        # execute the file
        subprocess.run([s], check=False)

    if executable("/etc/acq400/0/on_sync_role"):
        execute("/etc/acq400/0/on_sync_role")
    # Configure distributor (XO) after AI.
    config_distributor_sites(f"{trg.d_trg}")

    with open("/dev/shm/role", "w") as f:
        f.write(f"{CMDLINE}\n")
    with open("/dev/shm/role_fs_hz", "w") as f:
        f.write(f"{freq.fs}\n")
    return 0


if __name__ == "__main__":
    with simple_console_logger() as log:
        main()
