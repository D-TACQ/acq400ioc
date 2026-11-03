#!/bin/sh
# sync_role.common
# set.site 0 sync_role fpmaster|rpmaster|master|solo|slave FS FIN [opts] 
import sys
from pathlib import Path

roles = {}
acq1014_roles = {}
def fpmaster():
	set_common()
	set_out()
	$set_common_master
	set.site 0 SYS:CLK:FPMUX FPCLK
	set.site 0 SIG:SRC:TRG:0 EXT
	set_master $FS $FIN

def rpmaster():
	set_common()
	set_out()
	$set_slave 0
	$set_common_master
	set.site 0 SIG:SRC:TRG:0 HDMI
	set.site 0 SYS:CLK:FPMUX ZCLK
	set.site 0 SIG:ZCLK_SRC CLK.d0
	set_master() $FS $FIN

def master():
	set_common()
	set_out()
	D_TRG='d1'
	$set_common_master
	set_local_clock $FS
	is_48x && set_48x_override $FS master

def solo():
	set_common()
	set_local_clock $FS

def slave():
	set_common()
	set_out_slave()
	$set_slave
	is_48x && set_48x_override $FS slave
	is_43x && set_43x_override $FS slave

def slavemb():
	set_common()
	set_out_slave()
	$set_slave 0
	set.site 0 SIG:ZCLK_SRC CLK.d0
	set.site 0 SYS:CLK:FPMUX ZCLK
	set.site 0 SIG:CLK_MB:FIN $FIN
	$set_mb $FS
	set.site 0 SIG:SRC:CLK:1 MCLK

def acq1014_master_solo():
		TRG=${TRG:-int}
		D_TRG='d1'
		set_common
		/usr/local/bin/acq1014_select_clk_src int $FS $FIN_CLKSTAR;;

def acq1014_fpmaster():
		set_common
		if $acq1014_clk_src != 2:
			print("ERROR: RPCLK has priority"
			return 1
		else:
			/usr/local/bin/acq1014_select_clk_src ext $FS $FIN

def acq1014_rpmaster():
		set_common()
		if $acq1014_clk_src != 2:
			print("ERROR: RP CABLE NOT CONNECTED"
			return 1
		 else:
			/usr/local/bin/acq1014_select_clk_src ext $FS $FIN

def acq1014_slave():
		set_common()
		# Be careful with FIN. For slaves this is 20MHz for
		# rear panel masters this will be 1MHz.
		fin=$FIN_CLKSTAR
		[ "x$P3" != "x" ] && fin=$FIN
		/usr/local/bin/acq1014_select_clk_src ext $FS $fin

roles['fpmaster'] = fpmaster
roles['rpmaster'] = rpmaster
roles['master'] = master
roles['solo'] = solo
roles['slave'] = slave
roles['slavemb'] = slavemb

acq1014_roles['master'] = acq1014_master_solo
acq1014_roles['solo'] = acq1014_master_solo
acq1014_roles['fpmaster'] = acq1014_fpmaster
acq1014_roles['rpmaster'] = acq1014_rpmaster
acq1014_roles['slave'] = acq1014_slave


def set_mbclk():
	let fs=$1
	if [ $fs -lt $FMIN ]; then
	# ensure a valid fs, ignore any user CLKDIV
			let clkdiv="5*$FMIN/$fs"
			CLKDIV=$(printf "%d" $clkdiv)
			let fs=$CLKDIV*$fs
			set.site $S1 CLKDIV $CLKDIV
	else
			# assert CLKDIV, possibly user
			set.site $S1 CLKDIV $CLKDIV
	fi
	set.site 0 SIG:CLK_MB:SET $fs

set_mb=set_mbclk

def select_lo_zclk():
	set.site 0 SYS:CLK:FPMUX ZCLK
	set.site 0 SIG:ZCLK_SRC INT33M
	set.site 0 SIG:CLK_MB:FIN 33333000

def select_lo_xclk():
	set.site 0 SYS:CLK:FPMUX XCLK
	set.site 0 SIG:CLK_MB:FIN 32768000

select_lo=select_lo_zclk

def set_acq43x_sample_rate():
	set.site $S1 ACQ43X_SAMPLE_RATE $1

def sync_trg_to_clk():
	[ -e /etc/acq400/$S1/sync_trg_to_clk ] && \
		set.site $S1 sync_trg_to_clk $1



def set_slave_acq1001():
	set.site 0 SYS:CLK:FPMUX OFF
	sync_trg_to_clk 0
	set.site 0 SIG:SRC:CLK:${1:-1} HDMI
	set.site 0 SIG:SRC:TRG:0 HDMI
	set.site 0 SIG:SRC:SYNC:0 HDMI
	set.site $S1 "clk=1,d1,${CLK_SENSE}"
	set.site $S1 "trg=1,d0,${TRG_SENSE}"
	[ "x$ROLE" = "x${ROLE#*master}" ] && \
			[ -e /etc/acq400/$S1/sync ] && \
			set.site $S1 "sync=1,d0,rising"
	set.site $S1 CLKDIV=${CLKDIV:-1}


def set_slave_acq2106():
	set.site 0 SYS:CLK:OE_CLK1_ZYNQ 0
	set_slave_acq1001 $1


def set_common_master_acq1001():		
	set.site 0 SIG:SRC:CLK:1 MCLK
	sync_trg_to_clk 1
	[ -e /etc/acq400/$S1/ACQ43X_SAMPLE_RATE ] || set.site $S1 CLKDIV=${CLKDIV:-1}
	[ -e /etc/acq400/$S1/sync ] && set.site $S1 "sync=0,0,0"


def set_common_master_acq2106():
	set.site 0 SYS:CLK:OE_CLK1_ZYNQ 1
	set.site 0 SYS:CLK:BYPASS 0
	set_common_master_acq1001

is_48x():
	echo $MEZ | grep -q ACQ48


is_42x():
	echo $MEZ | egrep -q ACQ42\|AO42


is_43x():
	echo $MEZ | egrep -q ACQ43

# even a slave can master another link in the chain..
# we share the MB clock and the SITE trigger 
# The MASTER syncs the SITE trigger, SLAVES MUST leave it untouched.
def set_out(): 
	set.site 0 SIG:SYNC_OUT:CLK		CLK
	set.site 0 SIG:SYNC_OUT:CLK:DX	${CLKDX_OUT}
	set.site 0 SIG:SYNC_OUT:TRG		TRG
	set.site 0 SIG:SYNC_OUT:TRG:DX	d2
	set.site 0 SIG:SYNC_OUT:SYNC	SYNC
	set.site 0 SIG:SYNC_OUT:SYNC:DX d2
	set.sys /dev/acq400.0.knobs/mod_en 1


def set_out_slave():
	set.site 0 SIG:SYNC_OUT:CLK		CLK
	set.site 0 SIG:SYNC_OUT:CLK:DX	d1
	set.site 0 SIG:SYNC_OUT:TRG		TRG
	set.site 0 SIG:SYNC_OUT:TRG:DX	d0
	set.site 0 SIG:SYNC_OUT:SYNC	SYNC
	set.site 0 SIG:SYNC_OUT:SYNC:DX d0
	set.sys /dev/acq400.0.knobs/mod_en 1

def set_48x_override():
	# Configure clock

	if [ "$2" = "master" ]; then
	if [ $is_acq2106 -ne 0 ]; then
				# Configure clock - This is NOT valid for FPCLK
					set.site 0 SIG:SRC:CLK:0 INT01M
					fin=1000000
	else
				zclk_src=INT33M
		fin=33333000
	fi
	else
			set.site 0 SIG:SRC:CLK:0 HDMI
			fin=$FIN
	fi
	set.site 0 SYS:CLK:FPMUX ZCLK
	set.site 0 SIG:ZCLK_SRC ${zclk_src:-CLK.d0}
	set.site 0 SIG:CLK_MB:FIN $fin
	$set_mb $1
	set.site 0 SIG:SRC:CLK:1 MCLK
	[ $is_acq2106 -ne 0 ] && set.site 0 SYS:CLK:OE_CLK1_ZYNQ 1
	set.site $S1 CLKDIV=${CLKDIV:-1}
	# Configure HDMI Clock out
	set.site 0 SIG:SYNC_OUT:CLK:DX	d0

def set_43x_override():
	hi_res_mode=1
	[ $1 -ge 52000 ] && hi_res_mode=0
	set.site $S1 hi_res_mode=$hi_res_mode

def config_distributor_sites():
	distributor_sites=$(get.site 0 distributor | awk '{ print $2 }' | awk -F= '{ print $2 }' | sed "s/,/ /g")
	[ "$distributor_sites" = "none" ] && return
	
	for site in $distributor_sites; do
		if [ $(get.site $site module_role) = "MASTER" ]; then
			set.site $site clk '1,1,1'
			set.site $site "trg=1,${TRG_DX:-$1},${TRG_SENSE:-rising}"
												set.site $site clkdiv=${CLKDIV:-1}
			set.site $site CLKDIV=${CLKDIV:-1}
		fi
	done

# common to all
# report init status - this will be overwritten on successful completion
def set_common():
		echo "WARNING:$CMDLINE incomplete" > /dev/shm/role
#		set.site 0 SIG:*:RESET=1	&

def pv_read_lock():
		caput -t $PV_BASE:1:$1:r.DISA $2 >/dev/null


def set_local_clock():  
	$select_lo
	$set_mb $1
	pv_read_lock CLK 1
	set.site $S1 "clk=1,${CLK_DX:-d1},${CLK_SENSE}"
	pv_read_lock CLK 0
	pv_read_lock TRG 1
	set.site $S1 "trg=1,${TRG_DX:-d1},${TRG_SENSE}"
	pv_read_lock TRG 0


def set_master():
	pv_read_lock CLK 1
	set.site $S1 "clk=1,${CLK_DX:-d1},${CLK_SENSE}"
	pv_read_lock CLK 0
	pv_read_lock TRG 1
	set.site $S1 "trg=1,${TRG_DX:-d0},${TRG_SENSE}"
	pv_read_lock TRG 0
	set.site 0 SIG:CLK_MB:FIN $2
	$set_mb $1

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
				config["TRG_DX"] = val	# not previously defined. actual dX line..
			elif key == "CLK:DX":
				config["CLK_DX"] = val
			elif key == "CLKDIV":
				config["CLKDIV"] = val
			else:
				print(f"error {key} not defined, file=sys.stderr)
		else:
			# positional argument (no "=" present)
			px = len(config["positionals"]
			if [ $key = $val ]; then
				case $px in
					1)	P1=$k;;
					2)	P2=$k;;
					3)	P3=$k;;
					*)	print("error discard parameter $px $k";;
				esac
				px=$(($px+1))
			else
				print("error $key not defined"
			fi;;
		esac
	done
	return 0

DEV_SHM_ROLE = Path("/dev/shm/role")
RUN0_LOG = Path("/etc/acq400/0/run0_log")
ACQ43X_SAMPLE_RATE = Path("/etc/acq400/$S1/ACQ43X_SAMPLE_RATE")
TRG=None
TRG_SENSE="rising"
CLK_SENSE="rising"
FMIN=4000000
CLKDIV=1
FIN_DEF=1000000
FIN_CLKSTAR=20000000
P1=None
P2=None
P3=None

def main():
	if sys.argv[1] == "":
		if DEV_SHM_ROLE.exists():
			print(DEV_SHM_ROLE.read_text())
		else:
			print("role not set")
		return 0
	elif sys.argv[1] == "help":
		print("USAGE sync_role {fpmaster|rpmaster|master|slave|slavemb|solo} [CLKHZ] [FIN]")
		print("modifiers [CLK|TRG:SENSE=falling|rising] [CLK|TRG:DX=d0|d1]")
		print("modifiers [TRG=int|ext]")
		print("modifiers [CLKDIV=div]")
		exit 0

	#echo busy > /dev/shm/role
	DEV_SHM_ROLE.write_text("busy")

	CMDLINE="$*"

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
	# set.site $S1 CLK=1 2>&1 > /dev/null



	if ACQ43X_SAMPLE_RATE.exists():
			select_lo=select_lo_xclk
			set_mb=set_acq43x_sample_rate
	fi

	MOD=$(get.site 0 MODEL)
	MEZ=$(get.site $S1 MODEL)

	CLKDX_OUT=d1

	case ${MOD:0:7} in
	acq2106|acq2206|acq1102)
			set_slave=set_slave_acq2106
			set_common_master=set_common_master_acq2106
	# Si5326 minimum output rate. 2M works for slave XO hardware
			FMIN=10000
			is_acq2106=1;;
	*)
			set_slave=set_slave_acq1001
			set_common_master=set_common_master_acq1001
	# ics527 minimum output rate
			FMIN=4000000
	# avoid local clkdiv on slow SLAVE SAR devices		
			is_42x && CLKDX_OUT=d2
			is_acq2106=0;;
	esac

	FS_DEF=200000
	is_48x && FS_DEF=20000000

	# PV readback on triplet en,dx,edge can cause errors, so lock it
	source /etc/profile.d/epics.sh
	PV_BASE=${IOC_HOST}

	# execution here...
	ROLE=$P1
	eval $(egu2int FS=${P2:-$FS_DEF} FIN=${P3:-$FIN_DEF})

	D_TRG='d0'

	if MOD[0:7] == "acq1014":
		TRG=${TRG:-ext}
		acq1014_clk_src=$(get.site 2 acq1014_clk)
		rc = acq1014_roles[ROLE]()
		if rc > 0:
			print("ERROR: role $1 not valid")
			return 1
		# Set the trigger dependent on role or TRG= override on command line
		# Assume post mode. TRG_DX is ignored for ACQ1014
		/usr/local/bin/acq1014_select_trg_src $TRG post $TRG_SENSE		
	elif:
		roles[ROLE]()
	else:
		print("ERROR: role $1 not valid")
		return 1

	[ -x /etc/acq400/0/on_sync_role ] && /etc/acq400/0/on_sync_role
	# Configure distributor (XO) after AI.
	config_distributor_sites $D_TRG

	with open("/dev/shm/role", "w") as f:
		f.writeline($CMDLINE)
	with open("/dev/shm/role_fs_hz", "w") as f:
		f.writeline($FS)
	return 0

if __name__ == "__main__":
	main()
