#!/usr/bin/env python

# generate host column of dhcpd.conf for csr.

import sys

try :
    hvnum = int (sys.argv[1])
    vmnum = int (sys.argv[2])
except :
    print "%s [HVNUM] [VMNUM]" % sys.argv[0]
    sys.exit (1)
                                

macaddr = "02:00:aa:02:%02d:%02d" % (hvnum, vmnum)


print "\thost csr-%d-%d {" %  (hvnum, vmnum)
print "\t\thardware ethernet %s;" % macaddr
print "\t\tfixed-address 172.16.30.%d;" % (((hvnum - 1) * 8) + vmnum + 200)
print "\t}"
