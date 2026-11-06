#!/usr/bin/python
"""
# sync_role.wr
set.site 0 sync_role fpmaster|rpmaster|master|solo|slave FS [FMB] [opts]
"""

import logging
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

# from typing import Callable


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


def set_site(site_number: int, *site_params_vals):
    """returns the output string from set.site"""
    site_parameter: str = ""
    site_parameter_value: str = ""
    if len(site_params_vals) == 2:
        site_parameter, site_parameter_value = site_params_vals
    elif len(site_params_vals) == 1:
        if "=" not in site_params_vals[0]:
            raise ValueError("Two arg set_site requires PARAM=VALUE")
        site_parameter, site_parameter_value = site_params_vals[0].split("=", 1)

    log.info(f"set.site {site_number} {site_parameter} {site_parameter_value}")
    if isinstance(site_number, int):
        site_number_str = str(site_number)
    elif isinstance(site_number, str):
        site_number_str = site_number
    if not isinstance(site_parameter, str) or not isinstance(site_parameter_value, str):
        raise TypeError("set_site set.site requires strings")
    return subprocess.run(
        ["set.site", site_number_str, site_parameter, site_parameter_value],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def get_site(site_number: int, site_parameter: str):
    """returns the output string from get.site"""
    if isinstance(site_number, int):
        site_number_str = str(site_number)
    if isinstance(site_number, str):
        site_number_str = site_number
    return subprocess.run(
        ["get.site", site_number_str, site_parameter],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def is_ds(site):
    """
    #!/bin/sh
    SITE=${SITE:-1}
    if [ -e /dev/acq400.$SITE.knobs/is_adc ]; then
        exec grep -q ds /dev/acq400.$SITE.knobs/is_adc
    else
        exit 1
    fi
    """
    p = Path(f"/dev/acq400.{site}.knobs/is_adc")
    if p.exists():
        if "ds" in p.read_text():
            return True
    else:
        return False


def _set_fmbdef_hrmode(fs: int, S1) -> bool:
    if freq.fs == 10000:
        freq.fmb_def = 5120000
        hrmode = 1
    elif freq.fs == 20000:
        freq.fmb_def = 10240000
        hrmode = 1
    elif freq.fs == 40000:
        freq.fmb_def = 20480000
        hrmode = 1
    elif freq.fs == 80000:
        freq.fmb_def = 20480000
        hrmode = 0
    elif freq.fs == 125000:
        freq.fmb_def = 32000000
        hrmode = 0
    elif freq.fs == 128000:
        freq.fmb_def = 32768000
        hrmode = 0
    else:
        print("ERROR: SR options 10k 20k 40k 80k 125k 128k")
        sys.exit(1)
    set_site(S1, "hi_res_mode", f"{hrmode}")
    return True


def wr_initialise_values(S1):
    if is_ds(S1):
        log.info("is ds")
        freq.fs_def = 40000
        if inputs.P2:
            freq.fs = egu2int(inputs.P2)
        else:
            freq.fs = egu2int(freq.fs_def)
        set_site(S1, "ACQ43X_SAMPLE_RATE", "0")
        _set_fmbdef_hrmode(freq.fs, S1)
    else:
        log.info("not is_ds()")
        clk.clkdiv = "unknown"
        if is_tiga():
            log.info("is_tiga")
            freq.fmb_def = 10000000
            freq.fs_def = 200000
            if inputs.P2:
                freq.fs = inputs.P2
            else:
                freq.fs = freq.fs_def
            if freq.fs == freq.fmb_def:
                clk.clkdiv = 1
        else:
            log.info("not is_tiga()")
            freq.fmb_def = 40000000
            freq.fs_def = 20000000
            if is_48x(S1):
                log.info("is 48x")
                freq.fs_def = 20000000
            else:
                log.info("not 48x")
        if inputs.P2:
            log.info("freq.fs set to input P2")
            freq.fs = egu2int(inputs.P2)
        else:
            freq.fs = freq.fs_def
        log.info(f"what is freq.fs? : {freq.fs} type({type(freq.fs)})")
        if int(freq.fs) > 100:
            log.info(f"{freq.fs} > 100")
            # freq.fs = str(freq.fs / 10000000) + "0M" # TODO: what are the consequences of commenting out this line?
            if freq.fs == freq.fmb_def:
                clk.clkdiv = 1
            else:
                plan = in_the_plan(freq.fs, freq.fmb_def)
                log.info(f"in_the_plan returned {plan}")
                if plan == "40M":
                    clk.clkdiv = 40_000_000 // freq.fs
                    log.info(
                        f"since in_the_plan returned {plan} clkdiv calculated {clk.clkdiv}"
                    )
                # if plan != freq.fmb_def:
                #    freq.fmb_def = plan
                #    clk.clkdiv = 1
        else:
            log.info("clkdiv set to unknown")
            clk.clkdiv = "unknown"

        if clk.clkdiv == "unknown":
            if inputs.P2:
                log.info("freq.fs set to input")
                freq.fs = egu2int(inputs.P2)
            else:
                log.info(f"freq.fs set to freq.fs_def {freq.fs_def}")
                freq.fs = egu2int(freq.fs_def)
            freq.fmb = egu2int(freq.fmb_def)
            clk.clkdiv = freq.fmb / freq.fs
            freq.fs = freq.fmb / clk.clkdiv
            print(f"calculated {clk.clkdiv}")
    return 0


def parse_args(args):
    config = {"positionals": []}
    for token in args[1:]:
        if "=" in token:
            key, val = token.split("=", 1)
            if key == "TRG:SENSE":
                config["TRG:SENSE"] = val
            elif key == "CLK:SENSE":
                config["CLK_SENSE"] = val
            elif key == "TRG":
                config["TRG"] = val  # int or ext, pick dX defaults for most boxes
                if val == "int":
                    config["TRG_DX"] = "d1"
                elif val == "ext":
                    config["TRG_DX"] = "d0"
            elif key == "TRG:DX":
                config["TRG_DX"] = val  # not previously defined. actual dX line.
            elif key == "CLK:DX":
                config["CLK_DX"] = val
            elif key == "CLKDIV":
                config["CLKDIV"] = val
            else:
                print(f"error {key} not defined", file=sys.stderr)
        else:
            if len(config["positionals"]) < 3:
                config["positionals"].append(token)
            else:
                print(f"error discard parameter {token}", file=sys.stderr)
    return config


def sync_trg_to_clk(S1, val):
    ETC_ACQ400_S1_SYNC_TRG_TO_CLK = Path(f"/etc/acq400/{S1}/sync_trg_to_clk")
    if ETC_ACQ400_S1_SYNC_TRG_TO_CLK.exists():
        set_site(S1, "sync_trg_to_clk", val)


def is_48x(S1):
    return "ACQ48" in get_site(S1, "MODEL")


def is_42x(S1):
    return "ACQ42" in get_site(S1, "MODEL") or "AO42" in get_site(S1, "MODEL")


def set_slave(S1, slave_site):
    if is_acq2106():
        set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", "0")
    set_site(0, "SYS:CLK:FPMUX", "OFF")
    sync_trg_to_clk(S1, "0")
    set_site(0, f"SIG:SRC:CLK:{slave_site}", "HDMI")
    set_site(0, "SIG:SRC:TRG:0", "HDMI")
    set_site(0, "SIG:SRC:SYNC:0", "HDMI")
    set_site(S1, f"clk=1,d1,{clk.clk_sense}")
    set_site(S1, f"trg=1,d0,{trg.trg_sense}")
    if "master" not in ROLE:  # TODO: and sync exists???
        set_site(S1, "sync=1,d0,rising")
    if not clk.clkdiv:
        clk.clkdiv = 1
    set_site(S1, f"CLKDIV={clk.clkdiv}")


def set_common_master(S1):
    if is_acq2106():
        set_site(0, "SYS:CLK:OE_CLK1_ZYNQ", "1")
        set_site(0, "SYS:CLK:BYPASS", "0")
    ETC_ACQ400_S1_ACQ43X_SAMPLE_RATE = Path(f"/etc/acq400/{S1}/ACQ43X_SAMPLE_RATE")
    set_site(0, "SIG:SRC:CLK:1", "MCLK")
    sync_trg_to_clk(S1, "1")
    if not ETC_ACQ400_S1_ACQ43X_SAMPLE_RATE.exists():
        if not clk.clkdiv:
            clk.clkdiv = 1
        set_site(S1, f"CLKDIV={clk.clkdiv}")
    set_site(S1, "sync=0,0,0")


# common to all
# report init status - this will be overwritten on successful completion
def set_common():
    DEV_SHM_ROLE.write_text(f"WARNING:{CMDLINE} incomplete")
    # set_site(0 SIG:*:RESET=1  &


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


def set_out_slave():
    set_site(0, "SIG:SYNC_OUT:CLK", "CLK")
    set_site(0, "SIG:SYNC_OUT:CLK:DX", "d1")
    set_site(0, "SIG:SYNC_OUT:TRG", "TRG")
    set_site(0, "SIG:SYNC_OUT:TRG:DX", "d0")
    set_site(0, "SIG:SYNC_OUT:SYNC", "SYNC")
    set_site(0, "SIG:SYNC_OUT:SYNC:DX", "d0")


def config_distributor_sites(D_TRG):
    distributor_sites = get_site(0, "distributor")
    # | awk '{ print $2 }' | awk -F= '{ print $2 }' | sed "s/,/ /g")
    results = []
    for line in distributor_sites.splitlines():
        tokens = line.split()
        if len(tokens) < 2:
            continue
        target = tokens[1]

        if "=" in target:
            val = target.split("=", 1)[1]
        else:
            val = ""
        results.append(val.replace(",", " "))

    distributor_sites = "\n".join(results)

    if distributor_sites == "none":
        return 0

    if not clk.clkdiv:
        clk.clkdiv = 1
    if not trg.trg_dx:
        trg.trg_dx = D_TRG
    if not trg.trg_sense:
        trg.trg_sense = "rising"
    for site in distributor_sites:
        if get_site(site, "module_role") == "MASTER":
            set_site(site, "clk", "1,1,1")
            set_site(site, f"CLKDIV={clk.clkdiv}")
            set_site(site, f"trg=1,{trg.trg_dx},{trg.trg_sense}")
    return 0


def pv_read_lock(pv, val):
    subprocess.run(
        ["caput", "-t", f"{PV_BASE}:1:{pv}:r.DISA", f"{val}"], check=False
    )  # >/dev/null


def set_local_clock(S1):
    if not clk.clk_dx:
        clk.clk_dx = "d1"
    if not trg.trg_dx:
        trg.trg_dx = "d1"
    pv_read_lock("CLK", "1")
    set_site(S1, f"clk=1,{clk.clk_dx},{clk.clk_sense}")
    pv_read_lock("CLK", "0")
    pv_read_lock("TRG", "1")
    set_site(S1, f"trg=1,{trg.trg_dx},{trg.trg_sense}")
    pv_read_lock("TRG", "0")


# execution here... FMB must match a valid load file eg 20M


def in_the_plan(fs_target, default_fmb):
    log.info(f"in_the_plan(fs_target={fs_target}, default_fmb={default_fmb})")
    # PLANS = "$(for file in /etc/si5326.d/si5326_31M25*txt; do fs=${file#*_31M25-}; echo ${fs%*.txt}; done)"
    directory = Path("/etc/si5326.d")
    prefix = "si5326_31M25-"
    # divide default_fmb and fs_target by 1 million and replace the decimal point with an M and stringify
    if fs_target >= 1000000:
        log.info("fs_target ~1M")
        fs_target = str(float(fs_target) / 1e6).replace(".", "M").rstrip("0")
    elif fs_target >= 100000:
        log.info("fs_target ~100k")
        fs_target = str(float(fs_target) / 1e3).replace(".", "k").rstrip("0")
    elif fs_target >= 10000:
        log.info("fs_target ~10k")
        fs_target = str(float(fs_target) / 1e3).replace(".", "k").rstrip("0")
    elif fs_target >= 1000:
        log.info("fs_target ~1k")
        fs_target = str(float(fs_target) / 1e3).replace(".", "k").rstrip("0")
    default_fmb = str(float(default_fmb) / 1e6).replace(".", "M").rstrip("0")
    plan_list = [
        path.stem.removeprefix(prefix.rstrip("-") + "-")
        for path in sorted(directory.glob("si5326_31M25*.txt"))
    ]
    PLANS = "\n".join(plan_list)
    for pl in plan_list:
        log.info(f"pl in plan_list: {pl}")
        log.info(f"does fs_target={fs_target} == pl={pl}")
        if fs_target == pl:
            return pl
    log.info(f"in_the_plan is returning {default_fmb}")
    return str(default_fmb)


def int_to_egu(x: int) -> str:

    log.info(f"int_to_egu({x})")
    try:
        x_in_mega = int(x) / 1000000
        return str(x_in_mega).replace(".", "M").rstrip("0")
    except ValueError as e:
        if isinstance(x, str):
            return x.rstrip("0")
        else:
            raise ValueError(e)


def wr(S1):
    global D_TRG
    set_local_clock(S1)
    set_common()
    set_out()
    D_TRG = "d1"
    set_common_master(S1)
    MOD = get_site(0, "MODEL")
    if MOD == "acq1102":
        log.info(f"running /usr/local/CARE/acq1102+WR.init {freq.fmb_def} {clk.clkdiv}")
        subprocess.run(
            ["/usr/local/CARE/acq1102+WR.init", f"{freq.fmb_def}", f"{clk.clkdiv}"],
            check=False,
        )
    else:
        log.info(
            f"running /usr/local/CARE/acq2106+WR.init fmb_def={int_to_egu(freq.fmb_def)} clkdiv={clk.clkdiv}"
        )
        subprocess.run(
            [
                "/usr/local/CARE/acq2106+WR.init",
                f"{int_to_egu(freq.fmb_def)}",
                f"{clk.clkdiv}",
            ],
            check=False,
        )
    # need to use sh explicitly as the file below is missing a shebang
    subprocess.run(
        ["sh", "/usr/local/CARE/route-WR-FP"], check=False
    )  # /usr/local/CARE/route-WR-FP    1>&2
    if ETC_ACQ400_0_ON_SYNC_ROLE.exists():
        subprocess.run(["/etc/acq400/0/on_sync_role"], check=False)
    # Configure distributor (XO) after AI.
    config_distributor_sites(D_TRG)
    DEV_SHM_ROLE.write_text(
        f"{CMDLINE} ;# FIN={freq.fin} FMB_DEF={freq.fmb_def} FIN_DEF={freq.fin_def}"
    )
    DEV_SHM_ROLE_FS_HZ.write_text(f"{freq.fs}")
    return 0


def is_acq2106():
    ans = False
    MOD = get_site("0", "MODEL")
    if MOD[0:7] in ["acq2106", "acq2206", "acq1102"]:
        ans = True
    return ans


def is_tiga():
    """
    [ -e /dev/acq400.0.knobs/wr_tai_trg_s1 ] && exit 0
    """
    p = Path("/dev/acq400.0.knobs/wr_tai_trg_s1")
    return bool(p.exists())


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


# Globals
DEV_SHM_ROLE = Path("/dev/shm/role")
DEV_SHM_ROLE_FS_HZ = Path("/dev/shm/role_fs_hz")
ETC_ACQ400_0_ON_SYNC_ROLE = Path("/etc/acq400/0/on_sync_role")
ETC_ACQ400_0_ON_SYNC_ROLE = Path("/etc/acq400/0/on_sync_role")
RUN0_LOG = Path("/etc/acq400/0/run0_log")

CMDLINE = None
ROLE = None
PV_BASE = None


@dataclass
class Clk:
    clk_sense: str = "rising"
    clkdiv: int = 1
    clkdx_out: str = ""
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
    # FIN_DEF = "31M25"
    fin_def: int = 31250000
    fin_clkstar: int = 20000000
    fin: int = -1
    fs: int = -1
    fs_def: int = 200000
    fmb_def: int = -1


@dataclass
class Inputs:
    P1: str = ""
    P2: int = 0
    P3: str = ""


clk = Clk()
freq = Freq()
trg = Trg()
inputs = Inputs()


def main():
    global PV_BASE
    global ROLE
    global CMDLINE
    roles = {}
    roles["wr"] = wr
    roles["fpmaster"] = wr
    roles["rpmaster"] = wr
    roles["master"] = wr
    roles["solo"] = wr
    roles["slave"] = wr
    roles["whiterabbit"] = wr

    clk.clkdx_out = "d1"

    # PV readback on triplet en,dx,edge can cause errors, so lock it
    env_vars = source_shell_script("/etc/profile.d/epics.sh")
    PV_BASE = env_vars["IOC_HOST"]

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

    set_site(S1, "CLK=1")  # 2>&1 > /dev/null
    arg1 = sys.argv[1]
    if len(sys.argv) < 2 or sys.argv[1] == "":
        if DEV_SHM_ROLE.exists():
            with DEV_SHM_ROLE.open() as f:
                f.readline()
        else:
            print("role not set")
        sys.exit(0)
    elif arg1 == "help":
        print(
            "USAGE sync_role {wr|whiterabbit|fpmaster|rpmaster|master|slave|solo} [CLKHZ] [FIN]"
        )
        print("modifiers [CLK|TRG:SENSE=falling|rising] [CLK|TRG:DX=d0|d1]")
        print("modifiers [TRG=int|ext]")
        print("modifiers [CLKDIV=div]")
        sys.exit(0)
    args = parse_args(sys.argv)
    pos = args.get("positionals", [])
    inputs.P1 = pos[0] if len(pos) > 0 else ""
    inputs.P2 = pos[1] if len(pos) > 1 else None
    inputs.P3 = pos[2] if len(pos) > 2 else ""
    wr_initialise_values(S1)

    ROLE = f"{inputs.P1}"

    CMDLINE = " ".join(sys.argv[1:])
    try:
        roles[ROLE](S1)
    except Exception:
        print(f"ERROR: role {ROLE} not valid")
        log.exception("Gone wrong")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    with simple_console_logger() as log:
        main()
