# create access to EPICS PV via site service. This is important for :
# a/ non-EPICS users to get access to EPICS information
# b/ portable, UUT-relative namespace - site service omits ${UUT}:${SITE}


make_site_custom_knobs() {
	site=$1
	special=$2
	for file in /usr/local/epics/scripts/SITE${site}/*${special} ; do
		if [ -e $file ]; then
			fn=$(basename $file)
			generic=${fn%.${special}}
			knob=${generic/./_}
			[ ! -L /etc/acq400/0/sync_role ] && ln -s $file /etc/acq400/${site}/$knob
		fi
	done
}

make_site0_knobs() {
	(
		cd /etc/acq400/0/
		rm -f fpmux		
	)
	[ -e /etc/acq400/0/wrtd_tx ] && make_site_custom_knobs 0 wr
	make_site_custom_knobs 0 common
	make_site_custom_knobs 0 $(cat /proc/device-tree/chosen/compatible_model)
	ln -s /usr/local/epics/scripts/set_burst_mode /etc/acq400/0/burst_mode
}


make_reset_knobs() {
	for site in $*; do
		if [ -e /etc/acq400/$site ]; then
			case $site in
			12)	re=:B:;;
			13) re=:A:;;
			*)  re=:$site:;;
			esac
			(
			echo '#!/bin/sh';
			grep $re.*RESET /tmp/records.dbl | \
				sed -e 's/^/caput -t /' -e 's/$/ 1/' \
			) >/etc/acq400/$site/RESET_CTR
			chmod a+rx /etc/acq400/$site/RESET_CTR
		fi
	done
}
make_epics_knobs() {
	if [ -e /tmp/epics_knobs_done ]; then
	       echo make_epics_knobs 2
		return
	fi
	RLP=${RL%.*}P.dbl
	grep  -v .[a-z]$ $RL | grep -v rawc64 | grep -v fan | grep -v mux  | grep -v clk0$ > $RLP
	
	
	mkdir -p /etc/acq400/S
	for PV in $(egrep SYS:[0-9][Vv]\|SYS:VA?\|SYS:vcc?\|Z:TEMP\|MGTD $RL)
	do
		NU=${PV#*:}
		make_caget $PV ${NU#*:} S
	done
	
	for PV in $(egrep :.:SIG $RLP)
	do
		NU=${PV#*:}
		SITE=${NU%%:*}
		case $PV in
			*SET|*READY|*BSY|*SRC*|*FIN|*OUT*|*USER*|*TRAIN_REQ|*SIG:DDS:FREQ|*SIG:FP*)
				make_caput $PV ${NU#*:} ${SITE};;
			*)
				make_caget $PV ${NU#*:} ${SITE};;
		esac
	done

	for PV in $(egrep CAL:E $RLP)
	do
		NU=${PV#*:}
		SITE=${NU%%:*}
		make_caget_w $PV ${NU#*:} ${SITE}	
	done	

	for PV in $(egrep -e AWG $RLP)
	do
		NU=${PV#*:}
		case ${PV} in
		*DIST|*ABO|*BURSTLEN)
			make_caput $PV ${NU#*:} ${NU%%:*};;
		*)
			make_caget $PV ${NU#*:} ${NU%%:*};;
		esac
	done
	for PV in $(egrep -e MODE:BLT $RLP)
	do
		NU=${PV#*:}
		case ${PV} in
		*SET*|*BUFFERS|*POST)
			make_caput $PV ${NU#*:} 0;;
		*)
			make_caget $PV ${NU#*:} 0;;
		esac
	done	
	for PV in $(egrep -e DECIM -e OSR $RLP)
	do
		NU=${PV#*:}
		make_caget $PV ${NU#*:} ${NU%%:*}
	done
	
	for PV in $(egrep -e FIR:01$ -e HPF:0[1-8] -e T50R -e ACQ480:MR \
			-e LFNS -e INVERT -e ACQ4.X_SAMPLE_RATE -e GAIN -e RANGE -e ACQ465 -e QEN -e PPW $RLP)
	do
		NU=${PV#*:}
		SITE=${NU%%:*}
		make_caput $PV ${NU#*:} ${SITE}		
	done

	for PV in $(egrep -e :SYS:CLK $RLP)
	do
		make_caput $PV ${PV#*:} 0
	done

        for PV in $(egrep -e R:S1 $RLP )
        do
                make_caget $PV ${PV#*0:} 0
        done


	for PV in $(egrep -e :[1-6]:CLK -e :[1-6]:TRG  -e :[1-6]:SYNC -e :[1-6]:EVE \
			  -e :1:RGM -e :1:RTM -e :[1-6]:XDT -e :1:DT -e :[1-6]:ANATRG $RLP \
			| grep -v ':[0-9a-z_]*$' )
	do		
		pv1=${PV#*:}
		site=${pv1%%:*}
		make_caput $PV ${pv1#*:} $site
	done

	for PV in $(egrep -e :[1-6]:.*_DELAY -e :[1-6]:READ_LAT -e :[1-6]:LATENCY -e WR:TRG $RLP \
			| grep -v ':[0-9a-z_]*$' )
	do		
		pv1=${PV#*:}
		site=${pv1%%:*}
		make_caput $PV ${pv1#*:} $site -n
	done	
	
	for PV in $(egrep -e GPG -e DO:[1-9] $RLP)
	do
		pv1=${PV#*:}
		site=${pv1%%:*}
		case $PV in
		*DBG*)
			make_caget $PV ${pv1#*:} $site;;
		*)
			make_caput $PV ${pv1#*:} $site;;
		esac
	done

	for PV in $(egrep -e SC32 $RLP)
	do
		pv1=${PV#*:}
		site=${pv1%%:*}
		make_caput $PV ${pv1#*:} $site
	done
	for PV in $(egrep -e MODE:TRANSIENT -e MODE:CONTINUOUS $RLP)
	do
		pv1=${PV#*:}
		make_caput $PV ${pv1#*:} 0
	done

	for PV in $(egrep -e FPGA:TEMP $RLP)
	do
		pv1=${PV#*:}
		make_caput $PV ${pv1#*:} 13
	done
		
	for PV in $(egrep -e MODE:T -e IOC_READY $RLP)
	do
		pv1=${PV#*:}
		kn1=${pv1#*:}
		if [ ! -e /etc/acq400/0/$kn1 ]; then
			# avoid repeating MODE:TRANSIENT from above
			if echo $pv1 | grep -q SET_; then
				make_caput $PV $kn1 0
			else
				make_caget $PV $kn1 0
			fi
		fi
	done

	for PV in $(egrep -e SLOWMON $RLP)
	do
		pv1=${PV#*:}
		kn1=${pv1#*:}
		[ -e /etc/acq400/0/$kn1 ] || make_caput $PV $kn1 0  
	done

	for PV in $(egrep -e 0:WR $RLP)
	do
		pv1=${PV#*:}
		kn1=${pv1#*:}
		if echo $pv1 | grep -q RESET; then
			make_caput $PV $kn1 11
		else
			make_caget $PV $kn1 11
		fi
	done

	for PV in $(egrep -e Si5326:TUNEPHASE:BUSY -e Si5326:TUNEPHASE:OK $RLP)
	do
		NU=${PV#*:}
		SITE=${NU%%:*}
		make_caget $PV ${NU#*:} ${SITE}
	done

	for PV in $(egrep -e COS:EN:L16 $RLP)
	do
		pv1=${PV#*:}
		site=${pv1%%:*}
		ln -s /usr/local/epics/scripts/COS_EN /etc/acq400/${site}/
	done

        for PV in $(egrep -e MGT.*TX_DISABLE$ $RLP)
        do
                sfp=$(echo $PV | awk -F: '{ print $4 }')
                case $sfp in
                1) make_caput $PV TX_DISABLE 13;;
                2) make_caput $PV TX_DISABLE 12;;
                3) make_caput $PV TX_DISABLE 11;;
                4) make_caput $PV TX_DISABLE 10;;
                esac
        done
	make_reset_knobs 0 12 13
		
	make_site0_knobs	

	killall voltsmon
	touch /dev/shm/volts.txt
	ln -s /dev/shm/volts.txt /etc/acq400/0/SYS_VOLTS
	daemon /usr/local/bin/voltsmon.epics
	echo make_epics_knobs_done >/tmp/epics_knobs_done
	if [ -e /usr/local/init/acq400_knobs.init ]; then
		/usr/local/init/acq400_knobs.init start
	fi
}
