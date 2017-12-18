# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Modified by Nabeel Akhtar for RINA NFV webnair using Ryu
# Oct 2016

"""
An OpenFlow 1.0 L2 learning switch implementation.
"""
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import icmp
import ConfigParser
import os
import random as R

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

configFile = os.path.join(SCRIPT_PATH, "nfv.config")

print "configFile", configFile

config = ConfigParser.ConfigParser()
config.readfp(open(configFile))

ip_dst = str(config.get('general', 'ip_dst'))
ip_s1 = str(config.get('general', 'ip_s1'))
ip_s2 = str(config.get('general', 'ip_s2'))

vnf1 = str(config.get('general', 'vnf1'))
vnf2 = str(config.get('general', 'vnf2'))
vnf1_interface = int(config.get('general', 'vnf1_interface'))
vnf2_interface = int(config.get('general', 'vnf2_interface'))

controller_type = str(config.get('general', 'controller_type'))

file_attackerList = config.get('general', 'file_attackerList')

file_path_pi = config.get('general', 'file_path_pi')

idle_to = 4
hard_to = 4

vnf_port = vnf1_interface


class nfv_controller(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(nfv_controller, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def add_flow(self, datapath, in_port, dst, src, actions):
        ofproto = datapath.ofproto

        #match = datapath.ofproto_parser.OFPMatch(in_port=in_port, dl_dst=haddr_to_bin(dst)) # not adding dl_src=haddr_to_bin(src) here!

        match = datapath.ofproto_parser.OFPMatch(in_port=in_port, dl_dst=haddr_to_bin(dst), dl_src=haddr_to_bin(src))

        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=idle_to, hard_timeout=hard_to,
            priority=ofproto.OFP_DEFAULT_PRIORITY,
            flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
        datapath.send_msg(mod)

    def PISelection(self):
        # get the value for load balancer from PI controller output file
        f = open(file_path_pi, 'r')
        txt = f.read()
        txt = txt.strip(' \n')
        # value is saved on 'X' variable
        X = float(txt.split('=')[1])

        # generate a uniform random number between 0 and 1
        ran = R.random()

        # if generated number is > X, then send to VNF1, else send to VNF2
        if ran > X:
            return vnf1_interface
        elif ran <= X:
            return vnf2_interface
        else:
            self.logger.info("Error reading PI-controller generated load file! Default using vnf1 ")
            return vnf1_interface
        return -1

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):

        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        pkt_icmp = pkt.get_protocol(icmp.icmp)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s", dpid, src, dst, msg.in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = msg.in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        # check if packet is from the blacklisted source
        if pkt_ipv4:
            checkRe = self.checkAttackerList(str(pkt_ipv4.src))
            if checkRe:
                self.logger.info("%s in attacker list, packet being droped!", pkt_ipv4.src)
                ########
                # add rule to send packet to dummy port and return
                actions = [datapath.ofproto_parser.OFPActionOutput(1000)]
                self.add_flow(datapath, msg.in_port, dst, src, actions)

                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                out = datapath.ofproto_parser.OFPPacketOut(
                    datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
                    actions=actions, data=data)
                datapath.send_msg(out)
                ########
                return

        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

        global vnf_port

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:

            # forward a duplicate to VNF (either vnf1 or vfn2)
            if pkt_ipv4:
                if pkt_ipv4.dst == ip_dst and (pkt_ipv4.src == ip_s1 or pkt_ipv4.src == ip_s2):

                    self.logger.info("pkt_ipv4.src %s ", pkt_ipv4.src)
                    self.logger.info("pkt_ipv4.dst %s ", pkt_ipv4.dst)

                    # if round robin controller, sent in RR fashion
                    if controller_type == 'RR':
                        if vnf_port == vnf1_interface:
                            vnf_port = vnf2_interface
                        else:
                            vnf_port = vnf1_interface

                    # if PI controller, use PISelection()
                    elif controller_type == 'PI':
                        vnf_port = self.PISelection()
                    else:
                        vnf_port = vnf1_interface

                    self.logger.info("output port for NFV Selected: %s", str(vnf_port))

                    actions.append(datapath.ofproto_parser.OFPActionOutput(vnf_port))

            self.add_flow(datapath, msg.in_port, dst, src, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no

        ofproto = msg.datapath.ofproto
        if reason == ofproto.OFPPR_ADD:
            self.logger.info("port added %s", port_no)
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info("port deleted %s", port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info("port modified %s", port_no)
        else:
            self.logger.info("Illeagal port state %s %s", port_no, reason)

    def checkAttackerList(self, incomingIP):
        array = []
        try:
            with open(file_attackerList, "r") as ins:
                for line in ins:
                    ip = line.rstrip()
                    if ip not in array:
                        array.append(ip)
        except:
            self.logger.info("cannot find attacker file at %s", str(file_attackerList))
            return False
        # print "attacker list:", array
        if incomingIP in array:
            return True
        else:
            return False









