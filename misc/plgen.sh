#!/bin/sh

# generate csr xml template for libvirt

HVNUM=$1
VMNUM=$2
BSNUM=$3
FUNUM=$4
FDNUM=$5

if [ ! "$FDNUM" ]; then
	echo "$0 HVNUM VMNUM BUSNUM UPLINKFUNCTION DOWNLINKFUNCTION"
	echo $FDNUM
	exit 1
fi

cat template/palo-xml-template.xml | \
	sed -e "s/HV/$HVNUM/g"	| \
	sed -e "s/VM/$VMNUM/g"	| \
	sed -e "s/BN/$BSNUM/g"	| \
	sed -e "s/FU/$FUNUM/g"	| \
	sed -e "s/FD/$FDNUM/g"	
