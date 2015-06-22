#!/usr/bin/env python

# update pa-vm configuration from tftp. 
# contrilling vm through telnet via v6 linklocal

import sys
import pexpect
from netaddr import EUI

try :
    hvnum = int (sys.argv[1])
    vmnum = int (sys.argv[2])
    username = sys.argv[3]
    password = sys.argv[4]
except :
    print "%s [HVNUM] [VMNUM] [username] [password]" % sys.argv[0]
    sys.exit (1)


intf = "shownet-mgmt"
macaddr = "02:00:aa:01:%02d:%02d" % (hvnum, vmnum)
config = "running-config-%d-%d.xml" % (hvnum, vmnum)
controller = "172.16.30.33"


mac = EUI (macaddr)
mgmtaddr = mac.ipv6_link_local ()


p = pexpect.spawn ("telnet %s%%%s" % (mgmtaddr, intf))

p.logfile_read = sys.stdout

p.expect (r'login: ')
p.send ("%s\n" % username)

p.expect (r'Password: ')
p.send ("%s\n" % password)

p.expect (r'grandslam@pa-vm> ')
p.send ("set cli pager off\n")

p.expect (r'grandslam@pa-vm> ')
p.send ("tftp import configuration from %s file %s\n" % (controller, config))

p.expect (r'grandslam@pa-vm> ')
p.send ("configure\n")

p.expect (r'grandslam@pa-vm# ')
p.send ("load config from %s\n" % config)

p.expect (r'grandslam@pa-vm# ')
p.send ("commit\n")

p.expect (r'grandslam@pa-vm# ')
p.send ("exit\n")

p.expect (r'grandslam@pa-vm> ')
p.send ("exit\n")


p.terminate ()
