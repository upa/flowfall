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
    def __init__ (self, port_num = 0) :
        self.port_num = port_num
        self.maclist = [] # string
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
    def __init__ (self, dpid = dpid) :
        self.dpid = dpid

        self.ports = {}
        self.ports[VNF_UP] = []
        self.ports[VNF_DOWN] = []
        self.ports[NON_UP] = []
        self.ports[NON_DOWN] = []

        self.uplink_ports = []
        self.downlink_ports = []

        return


    def add_port (self, port_type, port) :

        self.ports[port_type].append (port)

        if port_type == VNF_UP or port_type == NON_UP :
            self.uplink_ports.append (port)

        if port_type == VNF_DOWN or port_type == NON_DOWN :
            self.downlink_ports.append (port)

        return


    def get_port (self, port_type, key) :

        portlist = self.ports[port_type]

        if not portlist :
            return None

        return self.portlist[key % len (self.portlist)]


    def get_port_mac (self, port_type, key) :

        port = self.get_port (port_type, key)

        if not port :
            return None

        return [port.port_num, port.get_mac (key)]

    def dpid (self) :
        return self.dpid


    def is_from_uplink (self, port_num) :

        for port in self.ports[VNF_UP] :
            if port.port_num == port_num :
                return True

        for port in self.ports[NON_UP] :
            if port.port_num == port_num :
                return True

        return False


    def is_from_downlink (self, port_num) :

        if is_from_uplink (port_num) :
            return False

        return True


    def check_tos_vnf (self, tos) :
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
            print "install OFSwitch \"%d\"" % switch["dpid"]

            ofs = OFSwitch (dpid = switch["dpid"])

            for vnfupport in switch["vnf_up_ports"] :
                port = Port (port_num = vnfupport["port_num"])
                for mac in vnfupport["mac"] :
                    port.add_mac (mac)
                ofs.add_port (VNF_UP, port)

            for vnfdownport in switch["vnf_down_ports"] :
                port = Port (port_num = vnfdownport["port_num"])
                for mac in vnfdownport["mac"] :
                    port.add_mac (mac)
                ofs.add_port (VNF_DOWN, port)

            for nonupport in switch["non_up_ports"] :
                port = Port (port_num = nonupport["port_num"])
                for mac in nonupport["mac"] :
                    port.add_mac (mac)
                ofs.add_port (NON_UP, port)

            for nondownport in switch["non_down_ports"] :
                port = Port (port_num = nondownport["port_num"])
                for mac in nondownport["mac"] :
                    port.add_mac (mac)
                ofs.add_port (NON_DOWN, port)

            self.ofswitches.append (ofs)


        # convert ffconfig.prefixes to self.rtree (Radix Class)
        self.rtree = radix.Radix ()

        for prefix in ffconfig.prefixes :
            print "install prefix \"%s\"" % prefix["prefix"]

            rnode = self.rtree.add (prefix["prefix"])
            rnode.data["type"] = prefix["type"]


        return

    def find_ofs (self, dpid) :
        for ofs in self.ofswitches :
            if ofs.dpid == dpid :
                return ofs
        return None


    def is_from_client (self, ipaddr) :
        if self.rtree.search_best (ipaddr) :
            return True
        return False


    @set_ev_cls (dpset.EventDP)
    def dp_handler (self, ev) :
        if ev.enter :
            print "New DPID %s [ %s ]" \
                % (ev.dp.id, " ".join (map (str, ev.dp.ports)))
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
                > uplink   : MATCH in_port, source IP and ToS
                > downlink : MATCH in_port, destination IP

        3. check, is packet from NOT CLIENT and downlink ports ?
            -> set to NON-VNF uplink flow, and downlink flow (to in_port)
                > uplink   : MATCH in_port, source IP
                > downlink : MATCH in_port, destination IP

        4. check, is packet from uplink ports ?
            -> set to NON-VNF downlink flow with low priority
                > downlink : MATCH in_port, destination IP prefix (0.0.0.0/0)
                This flow is overwritten when client send a packet
                with service embedded TOS field.

        """

        msg = ev.msg
        dpid = ev.dp.id
        datapath = msg.datapath

        ofs = self.find_ofs (dpid)
        if not ofs :
            print "Switch DPID %d is not found !!" % dpid
            return

        pkt = packet.Packet (msg.data)
        in_port = msg.in_port
        eth = pkt.get_protocol (ethernet.ethernet)

        if eth.ethertype != ether.ETH_TYPE_8021Q :
            print "not untagged packet"
            return

        vlan = pkt.get_protocol (vlan.vlan)

        # check rule 1.
        if not vlan.ethertype != ether.ETH_TYPE_IP :

            if ofs.is_from_uplink (in_port) :
                # uplink to downlink
                [to_port, mac] = ofs.get_port_mac (NON_DOWN, 1)
            else :
                # downlink to uplink
                [to_port, mac] = ofs.get_port_mac (NON_UP, 1)

            match = datapath.ofproto_parserOFPMatch ()
            match.set_vlan_vid (vlan.vid)
            match.set_dl_type (vlan.ethertype)
            match.in_port = in_port

            actions = [datapath.ofproto_parser.OFPActionOutPut (to_port)]

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority ofproto.OFP_DEFAULT_PRIORITY,
                flags = None, actions = actions)
            datapath.send_msg (mod)
            return


        # check rule 2.
        ip = pkt.get_protocol (ipv4.ipv4)
        if ofs.is_from_downlink (in_port) and self.is_from_client (ip.ip_src) :

            if ofs.check_tos_vnf (ip.tos) :
                port_type = VNF_UP
            else :
                port_type = NON_UP

            key = ipv4_test_to_int (ip.src)
            [to_port, mac] = ofs.get_port_mac (port_type, key)

            # from downlink to uplink
            match = datapath.ofproto_parserOFPMatch ()
            match.set_vlan_vid (vlan.vid)
            match.set_dl_type (vlan.ethertype)
            match.set_ipv4_src (ip.src)
            match.nw_tos = ip.tos
            match.in_port = in_port

            actions = [
                datapath.ofproto_parser.OFPActionSetDlDst (haddr_to_bin (mac)),
                datapath.ofproto_parser.OFPActionOutPut (to_port)
                ]

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority ofproto.OFP_DEFAULT_PRIORITY,
                flags = None, actions = actions)
            datapath.send_msg (mod)


            # from uplink to downlink
            match = datapath.ofproto_parserOFPMatch ()
            match.set_vlan_vid (vlan.vid)
            match.set_dl_type (vlan.ethertype)
            match.set_ipv4_dst (ip.src)
            match.nw_tos = ip.tos
            match.in_port = to_port

            actions = [
                datapath.ofproto_parser.OFPActionSetDlDst (eth.src),
                datapath.ofproto_parser.OFPActionOutPut (in_port)
                ]

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority ofproto.OFP_DEFAULT_PRIORITY,
                flags = None, actions = actions)
            datapath.send_msg (mod)

            return

        # check rule 3.
        if ofs.is_from_downlink (in_port) :

            key = ipv4_test_to_int (ip.src)
            [to_port, mac] = ofs.get_port_mac (NON_UP, key)

            # from downlink to uplink
            match = datapath.ofproto_parserOFPMatch ()
            match.set_vlan_vid (vlan.vid)
            match.set_dl_type (vlan.ethertype)
            match.set_ipv4_src (ip.src)
            match.in_port = in_port

            actions = [
                datapath.ofproto_parser.OFPActionSetDlDst (haddr_to_bin (mac)),
                datapath.ofproto_parser.OFPActionOutPut (to_port)
                ]

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority ofproto.OFP_DEFAULT_PRIORITY,
                flags = None, actions = actions)
            datapath.send_msg (mod)


            # from uplink to downlink
            match = datapath.ofproto_parserOFPMatch ()
            match.set_vlan_vid (vlan.vid)
            match.set_dl_type (vlan.ethertype)
            match.set_ipv4_dst (ip.src)
            match.in_port = to_port

            actions = [
                datapath.ofproto_parser.OFPActionSetDlDst (eth.src),
                datapath.ofproto_parser.OFPActionOutPut (in_port)
                ]

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority ofproto.OFP_DEFAULT_PRIORITY,
                flags = None, actions = actions)
            datapath.send_msg (mod)

            return


        # check rule 4.
        if ofs.is_from_uplink (in_port) :

            key = ipv4_test_to_int (ip.dst)
            [to_port, mac] = ofs.get_port_mac (NON_DOWN, key)

            # from uplink to downlink
            match = datapath.ofproto_parserOFPMatch ()
            match.set_vlan_vid (vlan.vid)
            match.set_dl_type (vlan.ethertype)
            match.set_ipv4_dst (ip.dst)
            match.in_port = in_port

            actions = [
                datapath.ofproto_parser.OFPActionSetDlDst (haddr_to_bin (mac)),
                datapath.ofproto_parser.OFPActionOutPut (to_port)
                ]

            mod = datapath.ofproto_parser.OFPFlowMod (
                datapath = datapath, match = match, cookie = 0,
                command = ofproto.OFPFC_ADD, idle_timeout = IDLE_TIMEOUT,
                hard_timeout = 0, priority ofproto.OFP_DEFAULT_PRIORITY,
                flags = None, actions = actions)
            datapath.send_msg (mod)

            return

        # not reahced
        print "packet-in: all rule is not matched !!"
        return
