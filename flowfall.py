#
#    FlowFall Controller
#

import types
import logging
import struct
import json
import radix

from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller import dpset
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ether
from ryu.lib import addrconv
from ryu.lib.mac import haddr_to_bin, haddr_to_str
from ryu.lib.ip import ipv4_to_bin, ipv4_to_str
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import vlan
from ryu.lib.packet import ipv4

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


# static variables
IDLE_TIMEOUT = 30


# port_type
VNF_UP   = 0 # to vnf uplink port
VNF_DOWN = 1 # to vnf downlink port
NON_UP   = 2 # pass uplink port
NON_DOWN = 3 # pass downlink port


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




class OFSwitch () :
    def __init__ (self, dpid) :
        self.dpid = dpid

        self.vlans = {}

        self.uplink_ports = []
        self.downlink_ports = []

        self.servicebit = False

        return


    def add_vlan (self, vlan) :
        if self.vlans.has_key (vlan) :
            return

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

        if not self.vlans.has_key (vlan) :
            print "invalid vlan id %d for dpid %d" % (vlan, self.dpid)
            return False

        portlist = self.vlans[vlan][port_type]

        if not portlist :
            return None

        return portlist[key % len (portlist)]


    def get_port_mac (self, vlan, port_type, key) :

        port = self.get_port (vlan, port_type, key)

        if not port :
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

        # XXX: check ToS field
        return True


class FlowFall (app_manager.RyuApp) :
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    _CONTEXTS = { 'dpset' : dpset.DPSet, }


    def __init__ (self, *args, **kwargs) :
        super (FlowFall, self).__init__ (*args, **kwargs)
        print "FlowFall is now starting"

        # convert ffconfig.ofswitches to self.ofswitches (OFSwitch Class)
        self.ofswitches = []

        for switch in ffconfig.ofswitches :
            print "install OFSwitch DPID:%d" % switch["dpid"]

            ofs = OFSwitch (switch["dpid"])
            ofs.servicebit = switch["servicebit"]

            for vlan in switch["vlan"].keys () :

                print "install vlan id %d info" % vlan

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


        # convert ffconfig.prefixes to self.rtree (Radix Class)
        self.rtree = radix.Radix ()

        for prefix in ffconfig.prefixes :
            print "install prefix %s" % prefix["prefix"]

            rnode = self.rtree.add (prefix["prefix"])
            rnode.data["type"] = prefix["type"]


        return

    def find_ofs (self, dpid) :
        for ofs in self.ofswitches :
            if ofs.dpid == dpid :
                return ofs
        return None


    def is_from_client (self, ipaddr) :
        rnode = self.rtree.search_best (ipaddr)

        if not rnode :
            return False

        if rnode.data["type"] != "CLIENT" :
            return False

        return True


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
        1. check, is packet NOT ETHER_TYPE_IP ?
            -> if from uplink, set to NON_DOWN port
            -> if from downlink, set to NON_UP port

        2. check, is packet from CLIENT and downlink ports ?
            -> check ToS and decide uplink port
            -> set to uplink flow, and downlink flow (to in_port)
                > uplink   : MATCH in_port, source IP and ToS, to to_port
                > downlink : MATCH to_port, destination IP, to in_port

        3. check, is packet from NOT CLIENT and downlink ports ?
            -> set to NON-VNF uplink flow, and downlink flow (to in_port)
                > uplink   : MATCH in_port, source IP, to to_port
                > downlink : MATCH to_port, destination IP, to in_port

        4. check, is packet from uplink ports ?
            -> set to NON-VNF downlink flow with low priority
                > downlink : MATCH in_port, destination IP prefix (0.0.0.0/0)
                This flow is overwritten when client send a packet
                with service embedded TOS field.

        """

        msg = ev.msg
        dpid = msg.datapath.id
        datapath = msg.datapath
        ofproto = datapath.ofproto

        print "packet in from DPID %d" % dpid

        ofs = self.find_ofs (dpid)
        if not ofs :
            print "Switch DPID %d is not found !!" % dpid
            return

        pkt = packet.Packet (msg.data)
        in_port = msg.in_port
        eth = pkt.get_protocol (ethernet.ethernet)

        if not ofs.find_port (in_port) :
            print "Packet-in from not configured port %d on DPID %d" \
                % (in_port, dpid)
            return

        if eth.ethertype == ether.ETH_TYPE_8021Q :
            is_tagged_packet = True
            vlanpkt = pkt.get_protocol (vlan.vlan)
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
                return [dp.ofproto_parser.OFPActionStripVlan ()]

            if not in_port.tagged and to_port.tagged :
                # add vlan
                return [dp.ofproto_parser.OFPActionVlanVid (to_port.vlan)]

            return []


        # check rule 1.
        print "rule 1"
        if ethertype != ether.ETH_TYPE_IP :

            if ofs.is_from_uplink (in_port) :
                # uplink to downlink
                [to_port, mac] = ofs.get_port_mac (vlan, NON_DOWN, 1)
            else :
                # downlink to uplink
                [to_port, mac] = ofs.get_port_mac (vlan, NON_UP, 1)

            match = datapath.ofproto_parser.OFPMatch (
                dl_type = ethertype,
                in_port = in_port)

            act = prepare_vlan_action (datapath, ofs, in_port, to_port)
            act.append (datapath.ofproto_parser.OFPActionOutput (to_port))

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority = ofproto.OFP_DEFAULT_PRIORITY,
                flags = 0, actions = act)
            datapath.send_msg (mod)
            return


        # check rule 2.
        print "rule 2"
        ip = pkt.get_protocol (ipv4.ipv4)
        if ofs.is_from_downlink (in_port) and self.is_from_client (ip.src) :

            if ofs.check_tos_vnf (ip.tos) :
                port_type = VNF_UP
            else :
                port_type = NON_UP

            key = ipv4_text_to_int (ip.src)
            [to_port, mac] = ofs.get_port_mac (vlan, port_type, key)

            # from downlink to uplink
            match = datapath.ofproto_parser.OFPMatch (
                in_port = in_port,
                dl_type = ethertype,
                nw_src = ipv4_text_to_int (ip.src),
                nw_tos = ip.tos)

            bmac = haddr_to_bin (mac)

            act = prepare_vlan_action (datapath, ofs, in_port, to_port)
            act.append (datapath.ofproto_parser.OFPActionSetDlDst (bmac))
            act.append (datapath.ofproto_parser.OFPActionOutput (to_port))

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority = ofproto.OFP_DEFAULT_PRIORITY,
                flags = 0, actions = act)
            datapath.send_msg (mod)


            # from uplink to downlink
            match = datapath.ofproto_parser.OFPMatch (
                in_port = to_port,
                dl_type = ethertype,
                nw_dst = ipv4_text_to_int (ip.src))

            bmac = haddt_to_bin (eth.src)

            act = prepare_vlan_action (datapath, ofs, to_port, in_port)
            act.append (datapath.ofproto_parser.OFPActionSetDlDst (bmac))
            act.append (datapath.ofproto_parser.OFPActionOutput (in_port))

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority = ofproto.OFP_DEFAULT_PRIORITY,
                flags = 0, actions = act)
            datapath.send_msg (mod)

            return

        # check rule 3.
        print "rule 3"
        if ofs.is_from_downlink (in_port) :

            key = ipv4_text_to_int (ip.src)
            [to_port, mac] = ofs.get_port_mac (vlan, NON_UP, key)

            # from downlink to uplink
            match = datapath.ofproto_parser.OFPMatch (
                in_port = in_port,
                dl_type = ethertype,
                nw_src = ipv4_text_to_int (ip.src))

            bmac = haddr_to_bin (mac)

            act = prepare_vlan_action (datapath, ofs, in_port, to_port)
            act.append (datapath.ofproto_parser.OFPActionSetDlDst (bmac))
            act.append (datapath.ofproto_parser.OFPActionOutput (to_port))

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority = ofproto.OFP_DEFAULT_PRIORITY,
                flags = 0, actions = act)
            datapath.send_msg (mod)


            # from uplink to downlink
            match = datapath.ofproto_parser.OFPMatch (
                in_port = to_port,
                dl_type = ethertype,
                nw_dst = ipv4_text_to_int (ip.src))

            bmac = haddr_to_bin (eth.src)

            act = prepare_vlan_action (datapath, ofs, to_port, in_port)
            act.append (datapath.ofproto_parser.OFPActionSetDlDst (bmac))
            act.append (datapath.ofproto_parser.OFPActionOutput (in_port))

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority = ofproto.OFP_DEFAULT_PRIORITY,
                flags = 0, actions = act)
            datapath.send_msg (mod)

            return


        # check rule 4.
        print "rule 4"
        if ofs.is_from_uplink (in_port) :

            key = ipv4_text_to_int (ip.dst)
            [to_port, mac] = ofs.get_port_mac (vlan, NON_DOWN, key)

            # from uplink to downlink
            match = datapath.ofproto_parser.OFPMatch (
                in_port = in_port
                dl_type = ethertype
                nw_src = ipv4_text_to_int (ip.dst))

            bmac = haddr_to_bin (mac)

            act = prepare_vlan_action (datapath, ofs, in_port, to_port)
            act.append (datapath.ofproto_parser.OFPActionSetDlDst (bmac))
            act.append (datapath.ofproto_parser.OFPActionOutput (to_port))

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority = ofproto.OFP_DEFAULT_PRIORITY,
                flags = 0, actions = act)
            datapath.send_msg (mod)

            return

        # not reahced
        print "packet-in: all rule is not matched !!"
        return
