# table of mtypes


MT_ACQ2006=80
MT_ACQ1001=81
MT_ACQ2106=82
MT_ACQ2206=87

MT_ACQ420=1
MT_ACQ420F=A1
MT_ACQ435=2
MT_ACQ430=3
MT_ACQ424=4
MT_ACQ425=5
MT_ACQ425F=A5
MT_ACQ426=C
MT_ACQ427=7
MT_ACQ427F=A7
MT_ACQ436=6D
MT_ACQ437=6
MT_ACQ465=A
MT_ACQ480=8
MT_ACQ423=9
MT_BOLO8=60
MT_DIO432=61
MT_DIO432P=62
MT_PMODAD1=63
MT_BOLO8B=64
MT_DIOB=67
MT_AO420=40
MT_AO424=41
MT_AO4220=42
MT_AO422=44
MT_PIG_CELF=68
MT_RAD_CELF=69
MT_AO428=6A
MT_DIO482=6B
MT_WER_CELF=70
MT_DIO482TD=7A
MT_DIO482TD_PG=7B
MT_ACQ494=B
MT_DIO422=71
MT_DI460=72
MT_DIO_5CH=73

MTV_DIO482_PPW="7A E"

get_mtv() {
    case $1 in
    [1-6])
        echo $(cd /etc/acq400/$1; cat module_type module_variant);;
    esac
}

nameFromMT() {
	mt=$(echo $1 | sed -e s/^0//)
        echo 1>&2 nameFromMT arg:$1 mt $mt
	case $mt in
	$MT_ACQ2006)	echo "acq2006";;
	$MT_ACQ1001)	echo "acq1001";;
	$MT_ACQ2106)	echo "acq2106";;
	$MT_ACQ2206)	echo "acq2206";;
	$MT_ACQ420|$MT_ACQ420F)
			echo "acq420";;	
	$MT_ACQ435)	echo "acq435";;
	$MT_ACQ430)	echo "acq430";;
	$MT_ACQ423)     echo "acq423";;
	$MT_ACQ424)	echo "acq424";;
	$MT_ACQ425|$MT_ACQ425F)		
			echo "acq425";;
	$MT_ACQ426)
	                echo "acq426";;
	$MT_ACQ427|$MT_ACQ427F)	
			echo "acq427";;
	$MT_ACQ436)	echo "acq436";;
	$MT_ACQ437)	echo "acq437";;
	$MT_ACQ465)     echo "acq465";;
	$MT_ACQ480)	echo "acq480";;
	$MT_BOLO8)	echo "bolo8";;
	$MT_DIO432|$MT_DIO432P)
			echo "dio432";;
	$MT_DIO482)	echo "dio432";;
	$MT_PMODAD1)	echo "pmodad1";;
	$MT_BOLO8B)	echo "bolo8B";;
	$MT_DIOB)	echo "diobiscuit";;
	$MT_AO420|$MT_AO4220)		
	                echo "ao420";;
	$MT_AO422)
	                echo "ao422";;
	$MT_AO424)		echo "ao424";;
	$MT_PIG_CELF)	echo "pig-celf";;
	$MT_RAD_CELF)	echo "rad-celf";;
	$MT_WER_CELF)   echo "wer-celf";;
	$MT_AO428)		echo "ao428elf";;
	$MT_DIO482TD)   echo "dio482td";;
	$MT_DIO482TD_PG) echo "dio482td_pg";;
	$MT_ACQ494)     echo "acq494fmc";;
	$MT_DIO422)     echo "dio422elf";;
	$MT_DI460)      echo "di460elf";;
	# no default	
	esac					
}

hasInput() {
case $(nameFromMT $1) in
	acq*|bolo*) echo "yes";;
	*) echo "no";;
	esac	
}
hasOutput() {
	mt=$(echo $1 | sed -e s/^0//)
	case $mt in
	$MT_DIO432|$MT_DIO432P|$MT_DIO482TD|$MT_DIO482TD_PG|$MT_DIO482|$MT_AO420|$MT_AO422|$MT_AO4220|$MT_AO424|$MT_AO428|$MT_ACQ436|$MT_DIO422) echo "yes";;
	*) echo "no";;
	esac
}

isDIO() {
	mt=$(echo $1 | sed -e s/^0//)
	case $mt in
	$MT_DIO432|$MT_DIO432P|$MT_DIO482TD|$MT_DIO482TD_PG|$MT_DIO482) echo "yes";;
	*) echo "no";;
	esac
}

isACQ43x() {
	mt=$(echo $1 | sed -e s/^0//)
	case $mt in
	$MT_ACQ430|$MT_ACQ435|$MT_ACQ436|$MT_ACQ437) echo "yes";;
	*) echo "no";;
	esac
}

hasNACC_BYPASS() {
	mt=$(echo $1 | sed -e s/^0//)
	case $mt in
	$MT_ACQ423|$MT_ACQ424|$MT_ACQ425|$MT_ACQ435) echo "yes";;
	*) echo "no";;
	esac
}
