# sourced from acq400ioc.init
# create access to EPICS PV via site service. This is important for :
# a/ non-EPICS users to get access to EPICS information
# b/ portable, UUT-relative namespace - site service omits ${UUT}:${SITE}

make_caget() {
	PFX=${1%*:$2}
	VERB=/usr/local/bin/caget_$PFX
	if [ ! -e $VERB ]; then
cat - >$VERB <<EOF
#!/bin/sh
PV=${PFX}:\$(basename \${0})
export EPICS_CA_AUTO_ADDR_LIST=NO EPICS_CA_ADDR_LIST=127.0.0.1
VALUE=\$(caget -s \${PV})
if [ \$? -eq 0 ]; then
	echo \${VALUE#${PFX}:}
else
	echo \${VALUE}
fi
EOF
		chmod 0555 $VERB
	fi
	ln -s $VERB /etc/acq400/$3/$2
}


make_caget_terse() {
        PFX=${1%*:$2}
        VERB=/usr/local/bin/caget_t_$PFX
        if [ ! -e $VERB ]; then
cat - >$VERB <<EOF
#!/bin/sh
PV=${PFX}:\$(basename \${0})
export EPICS_CA_AUTO_ADDR_LIST=NO EPICS_CA_ADDR_LIST=127.0.0.1
VALUE=\$(caget -t \${PV})
if [ \$? -eq 0 ]; then
        echo ${VALUE}
else
        echo ERROR \${VALUE}
fi
EOF
                chmod 0555 $VERB                
        fi
        ln -s $VERB /etc/acq400/$3/$2
}

make_caget_w() {
	PFX=${1%*:$2}
	VERB=/usr/local/bin/caget_w_$PFX
	if [ ! -e $VERB ]; then
cat - >$VERB <<EOF
#!/bin/sh
PV=${PFX}:\$(basename \${0})
export EPICS_CA_AUTO_ADDR_LIST=NO EPICS_CA_ADDR_LIST=127.0.0.1
VALUE=\$(caget \${PV})
if [ \$? -eq 0 ]; then
	echo \${VALUE#${PFX}:}
else
	echo \${VALUE}
fi
EOF
		chmod a+rx $VERB		
	fi
	ln -s $VERB /etc/acq400/$3/$2	
}

make_caput() {
	PFX=${1%*:$2}
	
	VERB=/usr/local/bin/caput_$PFX
	if [ ! -e $VERB ]; then
cat - >$VERB <<EOF
#!/bin/sh
PV=${PFX}:\$(basename \${0})
export EPICS_CA_AUTO_ADDR_LIST=NO EPICS_CA_ADDR_LIST=127.0.0.1
if [ "\$1" = "" ]; then
	VALUE=\$(caget ${4:--s} \${PV})
	if [ \$? -eq 0 ]; then
			echo \${VALUE#${PFX}:}
	else
			echo \${VALUE}
	fi
else
	VALUE=\$(caput \${PV} \$1)
	if [ \$? -ne 0 ]; then
		echo ERROR
	fi
fi 
EOF
		chmod a+rx $VERB		
	fi
	ln -s $VERB /etc/acq400/$3/$2
}
