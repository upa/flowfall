#!/bin/sh

# generate csr xml template for libvirt

HVNUM=$1
VMNUM=$2
SLNUM=$3
FUNUM=$4
FDNUM=$5

if [ ! "$FDNUM" ]; then
	echo "$0 HVNUM VMNUM VFSLOT UPLINKFUNCTION DOWNLINKFUNCTION"
	echo $FDNUM
	exit 1
fi

cat template/csr-xml-template.xml | \
	sed -e "s/HV/$HVNUM/g"	| \
	sed -e "s/VM/$VMNUM/g"	| \
	sed -e "s/SL/$SLNUM/g"	| \
	sed -e "s/FU/$FUNUM/g"	| \
	sed -e "s/FD/$FDNUM/g"	
