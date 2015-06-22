#
#    FlowFall Controller
#

import math
import types
import logging
import struct
import json
import radix
import hashlib

from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ether
from ryu.lib import addrconv
from ryu.lib.mac import haddr_to_bin, haddr_to_str
from ryu.lib.ip import ipv4_to_bin, ipv4_to_str
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import vlan as packetvlan
from ryu.lib.packet import ipv4

UINT32_MAX = 0xffffffff

import ffconfig

def mac_text_to_int(mac_text):
    if mac_text == 0:
        return mac_text
    assert isinstance(mac_text, str)
    return struct.unpack('!I', haddr_to_bin (mac_text))[0]


def ipv4_text_to_int(ip_text):
    if ip_text == 0:
        return ip_text
    assert isinstance(ip_text, str)
    return struct.unpack('!I', addrconv.ipv4.text_to_bin(ip_text))[0]


def mask_ntob(mask, err_msg=None):
    try:
        return (UINT32_MAX << (32 - mask)) & UINT32_MAX
    except ValueError:
        msg = 'illegal netmask'
        if err_msg is not None:
            msg = '%s %s' % (err_msg, msg)
        raise ValueError(msg)

# static variables
IDLE_TIMEOUT = 180
HARD_TIMEOUT = 0


# port_type
VNF_UP   = 0 # to vnf uplink port
VNF_DOWN = 1 # to vnf downlink port
NON_UP   = 2 # pass uplink port
NON_DOWN = 3 # pass downlink port

OFP_HIGH_PRIORITY = 0x9000


class FFLog () :
    def __init__ (self, use_stdout = True) :
        self.use_stdout = use_stdout
        self.progname = "flowfall"
        return

    def output_msg (self, level, msg) :
        msgout = "%s %s %s" % (self.progname, level, msg)

        if self.use_stdout :
            print msgout
        else :
            if level == "info" :
                logging.info (msgout)
            elif level == "warn" :
                logging.warning (msgout)
            elif level == "err" :
                logging.error (msgout)
            elif level == "debug" :
                logging.debug (msgout)
        return

    def info (self, msg) :
        self.output_msg ("info", msg)
        return

    def warn (self, msg) :
        self.output_msg ("warn", msg)
        return

    def err (self, msg) :
        self.output_msg ("err", msg)
        return

    def debug (self, msg) :
        self.output_msg ("debug", msg)
        return


class Port () :
    def __init__ (self, port_num, vlan) :
        self.port_num = port_num
        self.maclist = [] # string
        self.tagged = False
        self.vlan = vlan
        return


    def add_mac (self, mac) :
        if mac in self.maclist :
            return

        self.maclist.append (mac)
        return


    def get_mac (self, key) :
        if not self.maclist :
            return None

        return self.maclist[key % len (self.maclist)]


    def __repr__ (self) :
        return "%d" % self.port_num


class OFSwitch () :
    def __init__ (self, dpid, servicebit) :
        self.dpid = dpid
        self.servicebit = servicebit

        self.vlans = {}

        self.uplink_ports = []
        self.downlink_ports = []

        return


    def add_vlan (self, vlan) :
        if self.vlans.has_key (vlan) :
            return

        self.md5 = hashlib.md5 ()

        self.vlans[vlan] = {}
        self.vlans[vlan][VNF_UP] = []
        self.vlans[vlan][VNF_DOWN] = []
        self.vlans[vlan][NON_UP] = []
        self.vlans[vlan][NON_DOWN] = []
        return

    def add_port (self, vlan, port_type, port) :

        if not self.vlans.has_key (vlan) :
            print "invalid vlan id %d for dpid %d" % (vlan, self.dpid)
            return False

        self.vlans[vlan][port_type].append (port)

        if port_type == VNF_UP or port_type == NON_UP :
            self.uplink_ports.append (port)

        if port_type == VNF_DOWN or port_type == NON_DOWN :
            self.downlink_ports.append (port)

        return


    def get_port (self, vlan, port_type, key) :

        self.md5.update (str (key))
        hkey = int (self.md5.hexdigest (), 16)

        if not self.vlans.has_key (vlan) :
            print "invalid vlan id %d for dpid %d" % (vlan, self.dpid)
            return False

        portlist = self.vlans[vlan][port_type]

        if not portlist :
            return None

        return portlist[hkey % len (portlist)]


    def get_port_mac (self, vlan, port_type, key) :

        port = self.get_port (vlan, port_type, key)

        if not port :
            if VNF_UP : return self.get_port (vlan, NON_UP, key)
            if VNF_DOWN : return self.get_port (vlan, NON_DOWN, key)
            return None

        return [port.port_num, port.get_mac (key)]

    def dpid (self) :
        return self.dpid


    def is_from_uplink (self, port_num) :

        for port in self.uplink_ports :
            if port.port_num == port_num :
                return True

        return False


    def is_from_downlink (self, port_num) :

        if self.is_from_uplink (port_num) :
            return False

        return True


    def find_port (self, port_num) :

        for port in self.uplink_ports :
            if port.port_num == port_num :
                return port

        for port in self.downlink_ports :
            if port.port_num == port_num :
                return port

        return None

    def get_vlan_of_port (self, port_num) :

        port = self.find_port (port_num)
        if not port :
            return False
        return port.vlan


    def check_tos_vnf (self, tos) :

        if not self.servicebit :
            return False

        bitlist = [ 0, 0, 0, 0, 0, 0, 0, 0 ]

        bitrange = range (8)
        bitrange.reverse ()

        for x in bitrange :
            b = int (math.floor (tos / (2 ** x)))
            bitlist[x] = b
            tos -= b * (2 ** x)

        if bitlist[self.servicebit - 1] :
            return True

        return False


class FlowFall (app_manager.RyuApp) :
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = { 'dpset' : dpset.DPSet, }


    def __init__ (self, *args, **kwargs) :
        super (FlowFall, self).__init__ (*args, **kwargs)

        self.log = FFLog ()

        self.log.info ("Flowfall is now starting")


        # convert ffconfig.ofswitches to self.ofswitches (OFSwitch Class)
        self.ofswitches = []

        for switch in ffconfig.ofswitches :
            self.log.info ("install OFSwitch DPID:%d" % switch["dpid"])

            ofs = OFSwitch (switch["dpid"], switch["servicebit"])

            for vlan in switch["vlan"].keys () :

                self.log.info ("install vlan id %d info" % vlan)

                ofs.add_vlan (vlan)
                vlanfdb = switch["vlan"][vlan]

                for vnfupport in vlanfdb["vnf_up_ports"] :
                    port = Port (vnfupport["port_num"], vlan)
                    port.tagged = vnfupport["tagged"]
                    for mac in vnfupport["mac"] :
                        port.add_mac (mac)
                    ofs.add_port (vlan, VNF_UP, port)

                for vnfdownport in vlanfdb["vnf_down_ports"] :
                    port = Port (vnfdownport["port_num"], vlan)
                    port.tagged = vnfdownport["tagged"]
                    for mac in vnfdownport["mac"] :
                        port.add_mac (mac)
                    ofs.add_port (vlan, VNF_DOWN, port)

                for nonupport in vlanfdb["non_up_ports"] :
                    port = Port (nonupport["port_num"], vlan)
                    port.tagged = nonupport["tagged"]
                    for mac in nonupport["mac"] :
                        port.add_mac (mac)
                    ofs.add_port (vlan, NON_UP, port)

                for nondownport in vlanfdb["non_down_ports"] :
                    port = Port (nondownport["port_num"], vlan)
                    port.tagged = nondownport["tagged"]
                    for mac in nondownport["mac"] :
                        port.add_mac (mac)
                    ofs.add_port (vlan, NON_DOWN, port)

            self.ofswitches.append (ofs)
            self.log.info ("DPID %d uplink=%s, downlink=%s" % 
                           (ofs.dpid, ofs.uplink_ports, ofs.downlink_ports))

        # convert ffconfig.prefixes to self.rtree (Radix Class)
        self.rtree = radix.Radix ()

        for prefix in ffconfig.prefixes :
            self.log.info ("install prefix %s" % prefix["prefix"])

            rnode = self.rtree.add (prefix["prefix"])
            rnode.data["type"] = prefix["type"]
            [ pref, length ]  = prefix["prefix"].split ("/")
            rnode.data["prefix"] = pref
            rnode.data["length"] = int (length)

        self.log.info ("initialization finished.")

        return


    def find_ofs (self, dpid) :
        for ofs in self.ofswitches :
            if ofs.dpid == dpid :
                return ofs
        return None


    def is_from_client (self, ipaddr) :

        rnode = self.rtree.search_best (str (ipaddr))

        if not rnode :
            return False

        if rnode.data["type"] == "CLIENT" :
            return True

        return False


    def is_to_client (self, ipaddr) :

        rnode = self.rtree.search_best (str (ipaddr))

        if not rnode : 
            return False

        if rnode.data["type"] == "CLIENT" :
            return rnode.data

        return False


    def send_flowmod (self, datapath, priority, match, act,
                      idle = IDLE_TIMEOUT, hard = HARD_TIMEOUT) :

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        ins = [parser.OFPInstructionActions (ofproto.OFPIT_APPLY_ACTIONS, act)]
        mod = parser.OFPFlowMod (datapath = datapath, priority = priority,
                                 match = match, instructions = ins,
                                 idle_timeout = idle, hard_timeout = hard)

        datapath.send_msg (mod)
        print "send flow"
        print mod

        return


    def send_packetout (self, datapath, msg, actions) :

        data = None
        if msg.buffer_id == datapath.ofproto.OFP_NO_BUFFER :
            data = msg.data

        parser = datapath.ofproto_parser
        out = parser.OFPPacketOut (datapath = datapath,
                                   buffer_id = msg.buffer_id,
                                   in_port = msg.match['in_port'],
                                   actions = actions,
                                   data = data)

        datapath.send_msg (out)

        return

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install packet-in rule
        match = parser.OFPMatch ()
        actions = [parser.OFPActionOutput (ofproto.OFPP_CONTROLLER,
                                           ofproto.OFPCML_NO_BUFFER)]
        self.send_flowmod (datapath, 0, match, actions, idle = 0, hard = 0)
        return


    @set_ev_cls (dpset.EventDP)
    def dp_handler (self, ev) :
        if ev.enter :
            print "New DPID %s [ %s ]" \
                % (ev.dp.id, " ".join (map (str, ev.dp.ports)))

            if not self.find_ofs (ev.dp.id) :
                print "Unknown DPID %d !!" % ev.dp.id

        else :
            print "DPID %s leaved" % (ev.dp.id)

        return


    @set_ev_cls (ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler (self, ev) :
        """
        rule 1. check, is packet NOT ETHER_TYPE_IP ?
            -> if from uplink, set to NON_DOWN port
            -> if from downlink, set to NON_UP port

        rule 2. check, is packet from CLIENT and downlink ports ?
            -> check ToS and decide uplink port
            -> set to uplink flow, and downlink flow (to in_port)
                > uplink   : MATCH in_port, source IP and ToS, to to_port
                > downlink : MATCH to_port, destination IP, to in_port
            installing flows with High Priority to win rule 4

        rule 3. check, is packet from NOT CLIENT and downlink ports ?
            -> set to NON-VNF uplink flow, and downlink flow (to in_port)
                > uplink   : MATCH in_port, source IP, to to_port
                > downlink : MATCH to_port, destination IP, to in_port

        rule 4. check, is packet from uplink ports ?
            -> set to NON-VNF downlink flow with low priority
                > downlink : MATCH in_port, destination IP prefix (0.0.0.0/0)
                This flow is overwritten when client send a packet
                with service embedded TOS field.

        """

        msg = ev.msg
        dpid = msg.datapath.id
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        print "packet in from dpid %d" % dpid

        ofs = self.find_ofs (dpid)
        if not ofs :
            self.log.warn ("Switch DPID %d is not found !!" % dpid)
            return

        pkt = packet.Packet (msg.data)
        in_port = msg.match['in_port']
        eth = pkt.get_protocol (ethernet.ethernet)

        if not ofs.find_port (in_port) :
            self.log.warn ("Packet-in from not configured port %d on DPID %d."
                           % (in_port, dpid))
            return

        if eth.ethertype == ether.ETH_TYPE_8021Q :
            is_tagged_packet = True
            vlanpkt = pkt.get_protocol (packetvlan.vlan)
            vlan = vlanpkt.vid
            ethertype = vlanpkt.ethertype
        else :
            is_tagged_packet = False
            vlan = ofs.get_vlan_of_port (in_port)
            ethertype = eth.ethertype


        def prepare_vlan_action (dp, ofs, in_port_num, to_port_num) :
            in_port = ofs.find_port (in_port_num)
            to_port = ofs.find_port (to_port_num)

            if in_port.tagged and not to_port.tagged :
                # strip vlan
                return []
            #return [dp.ofproto_parser.OFPActionPopVlan ()]

            if not in_port.tagged and to_port.tagged :
                # add vlan
                f = dp.ofproto_parser.OFPMatchField.make (
                    dp.ofproto.OXM_OF_VLAN_VID, to_port.vlan)

                return [
                        dp.ofproto_parser.OFPActionSetField (f)]
                return []

            return []


        # check rule 1.
        if ethertype != ether.ETH_TYPE_IP :

            self.log.debug ("packet-in : from %s to %s on DPID %d port %d" %
                            (eth.src, eth.dst, dpid, in_port))

            self.log.info ("Rule 1 : not ETHER_TYPE_IP packet")

            if ofs.is_from_uplink (in_port) :
                # uplink to downlink
                [to_port, mac] = ofs.get_port_mac (vlan, NON_DOWN, 1)
            else :
                # downlink to uplink
                [to_port, mac] = ofs.get_port_mac (vlan, NON_UP, 1)

            match = parser.OFPMatch (eth_type = ethertype, in_port = in_port)

            act = prepare_vlan_action (datapath, ofs, in_port, to_port)
            #if mac :
            #    act.append (parser.OFPActionSetField (eth_dst = mac))
            act.append (parser.OFPActionOutput (to_port))

            prio = ofproto.OFP_DEFAULT_PRIORITY

            self.send_flowmod (datapath, prio, match, act)
            self.send_packetout (datapath, msg, act)

            self.log.info ("FlowMod 0x%x in_port %d to_port %d DPID %d" %
                           (ethertype, in_port, to_port, dpid))

            print
            return


        ip = pkt.get_protocol (ipv4.ipv4)
        self.log.debug ("packet-in : from %s to %s on DPID %d port %d" %
                        (ip.src, ip.dst, dpid, in_port))


        # check rule 2.
        if ofs.is_from_downlink (in_port) and self.is_from_client (ip.src) :

            self.log.info ("Rule 2 : from CLIENT prefix via downlink.")
            self.log.info ("tos is %d" % ip.tos)

            if ofs.check_tos_vnf (ip.tos) :
                port_type = VNF_UP
            else :
                port_type = NON_UP

            key = ipv4_text_to_int (ip.src)
            [to_port, mac] = ofs.get_port_mac (vlan, port_type, key)

            # from downlink to uplink
            match = parser.OFPMatch (
                in_port = in_port,
                eth_type = ethertype,
                ipv4_src = ipv4_text_to_int (ip.src),
                ip_dscp = ip.tos >> 2)

            act = prepare_vlan_action (datapath, ofs, in_port, to_port)
            if mac :
                act.append (parser.OFPActionSetField (eth_dst = mac))
            act.append (parser.OFPActionOutput (to_port))

            prio = OFP_HIGH_PRIORITY

            self.send_flowmod (datapath, prio, match, act)
            self.send_packetout (datapath, msg, act)

            self.log.info ("FlowMod %s->Any in_port %d to_port %d DPID %d"
                           % (ip.src, in_port, to_port, dpid))


            # from uplink to downlink
            match = parser.OFPMatch (
                in_port = to_port,
                eth_type = ethertype,
                ipv4_dst = ipv4_text_to_int (ip.src))

            act = prepare_vlan_action (datapath, ofs, to_port, in_port)
            act.append (parser.OFPActionSetField (eth_dst = eth.src))
            act.append (parser.OFPActionOutput (in_port))

            prio = OFP_HIGH_PRIORITY

            self.send_flowmod (datapath, prio, match, act)

            self.log.info ("FlowMod Any->%s in_port %d to_port %d DPID %d"
                           % (ip.src, to_port, in_port, dpid))

            print
            return


        # check rule 3.
        if ofs.is_from_downlink (in_port) :

            self.log.info ("Rule 3: from NOT CLIENT via downlink.")

            key = ipv4_text_to_int (ip.src)
            [to_port, mac] = ofs.get_port_mac (vlan, NON_UP, key)

            # from downlink to uplink
            match = parser.OFPMatch (
                in_port = in_port,
                eth_type = ethertype,
                ipv4_src = ipv4_text_to_int (ip.src))

            act = prepare_vlan_action (datapath, ofs, in_port, to_port)
            if mac :
                act.append (parser.OFPActionSetField (eth_dst = mac))
            act.append (parser.OFPActionOutput (to_port))

            prio = ofproto.OFP_DEFAULT_PRIORITY

            self.send_flowmod (datapath, prio, match, act)
            self.send_packetout (datapath, msg, act)

            self.log.info ("FlowMod %s->Any in_port %d to_port %d DPID %d"
                           % (ip.src, in_port, to_port, dpid))


            # from uplink to downlink
            match = parser.OFPMatch (
                in_port = to_port,
                eth_type = ethertype,
                ipv4_dst = ipv4_text_to_int (ip.src))

            act = prepare_vlan_action (datapath, ofs, to_port, in_port)
            act.append (parser.OFPActionSetField (eth_dst = eth.src))
            act.append (parser.OFPActionOutput (in_port))

            prio = ofproto.OFP_DEFAULT_PRIORITY

            self.send_flowmod (datapath, prio, match, act)

            self.log.info ("FlowMod Any->%s in_port %d to_port %d DPID %d"
                           % (ip.src, to_port, in_port, dpid))

            print
            return


        # check rule 4.
        if ofs.is_from_uplink (in_port) :

            self.log.info ("Rule 4 : from uplink.")

            key = ipv4_text_to_int (ip.dst)
            [to_port, mac] = ofs.get_port_mac (vlan, NON_DOWN, key)

            # from uplink to downlink
            match = parser.OFPMatch ()
            match.set_in_port (in_port)
            match.set_dl_type (ethertype)

            rdata = self.is_to_client (ip.dst)
            if rdata :
                maskbit = mask_ntob (rdata["length"])
                addrbit = ipv4_text_to_int (rdata["prefix"])
                match.set_ipv4_dst_masked (addrbit & maskbit, maskbit)
            else :
                match.set_ipv4_dst (ipv4_text_to_int (ip.dst))

            act = prepare_vlan_action (datapath, ofs, in_port, to_port)
            if mac :
                act.append (parser.OFPActionSetField (eth_dst = mac))
            act.append (parser.OFPActionOutput (to_port))

            prio = ofproto.OFP_DEFAULT_PRIORITY

            self.send_flowmod (datapath, prio, match, act)
            self.send_packetout (datapath, msg, act)

            self.log.info ("FlowMod Any->%s in_port %d to_port %d DPID %d"
                           % (ip.dst, in_port, to_port, dpid))

            print
            return

        # not reahced
        self.log.err ("All rule is not matched " +
                      "from %s to %s on DPID %d !!" % (ip.src, ip.dst, dpid))
        print
        return
