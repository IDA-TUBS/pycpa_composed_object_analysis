"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Builds common systems to be reused as a hardware setup for analysis.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from model_builder.cross_layer_model import clm



def create_automotive_ring_topology(r_generator = None, speed = "1Gbps", **kwargs):

    print("Create system: Automotive Ring Topologie")
    
    # Create the cross layer model system instance
    system = clm.CrossLayerModel(name='random_network_system')
   # print("Ring topology system")

    # ---- Init the network test setup ----
    # Init the switches
    system.add_switch("SW_VL",4,speed)
    system.add_switch("SW_VR",4,speed)
    system.add_switch("SW_HL",4,speed)
    system.add_switch("SW_HR",4,speed)

    # Connect the switches
    system.link_switch_to_switch(system.switches["SW_VL"],system.switches["SW_VR"])
    system.link_switch_to_switch(system.switches["SW_VR"],system.switches["SW_HR"])
    system.link_switch_to_switch(system.switches["SW_HR"],system.switches["SW_HL"])
    system.link_switch_to_switch(system.switches["SW_HL"],system.switches["SW_VL"])

    # Init dummy endpoints
    system.add_NIC_endpoint('NIC_VL_1',speed)
    system.add_NIC_endpoint('NIC_VL_2',speed)
    system.add_NIC_endpoint('NIC_VR_1',speed)
    system.add_NIC_endpoint('NIC_VR_2',speed)
    system.add_NIC_endpoint('NIC_HL_1',speed)
    system.add_NIC_endpoint('NIC_HL_2',speed)
    system.add_NIC_endpoint('NIC_HR_1',speed)
    system.add_NIC_endpoint('NIC_HR_2',speed)

    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_VL_1"],system.switches["SW_VL"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_VL_2"],system.switches["SW_VL"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_VR_1"],system.switches["SW_VR"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_VR_2"],system.switches["SW_VR"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_HL_1"],system.switches["SW_HL"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_HL_2"],system.switches["SW_HL"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_HR_1"],system.switches["SW_HR"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_HR_2"],system.switches["SW_HR"])


    sync_resource_allocation = dict()
    
    for key in system.switches:
        switch = system.switches[key]
        for i in range(0, switch.current_nbr_ports):
            sync_resource_allocation[switch.ports[i].name] = list()
    for key in system.NIC_endpoints:
        endpoint = system.NIC_endpoints[key]
        sync_resource_allocation[endpoint.port.name] = list()

    return system, sync_resource_allocation




def create_star_hardware_system(r_generator = None, speed = "1Gbps", **kwargs):

    print("Create system: Star topology use case")
    
    # ---- Init the network test setup ----
    # Init the switches
    system = clm.CrossLayerModel(name='random_network_system')
    
    system.add_switch("SW_0",7,speed)
    system.add_switch("SW_1",5,speed)
    
    
    # Connect the switches
    system.link_switch_to_switch(system.switches["SW_0"],system.switches["SW_1"])

    # Init dummy endpoints
    system.add_NIC_endpoint('NIC_0_0',speed)
    system.add_NIC_endpoint('NIC_0_1',speed)
    system.add_NIC_endpoint('NIC_0_2',speed)
    system.add_NIC_endpoint('NIC_0_3',speed)
    system.add_NIC_endpoint('NIC_0_4',speed)
    system.add_NIC_endpoint('NIC_0_5',speed)
    system.add_NIC_endpoint('NIC_1_0',speed)    
    system.add_NIC_endpoint('NIC_1_1',speed)
    system.add_NIC_endpoint('NIC_1_2',speed)
    system.add_NIC_endpoint('NIC_1_3',speed)
    
    
    # Connect endpoints to switches endpoints
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_0"],system.switches["SW_0"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_1"],system.switches["SW_0"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_2"],system.switches["SW_0"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_3"],system.switches["SW_0"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_4"],system.switches["SW_0"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_5"],system.switches["SW_0"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_1_0"],system.switches["SW_1"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_1_1"],system.switches["SW_1"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_1_2"],system.switches["SW_1"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_1_3"],system.switches["SW_1"])
    
    
    
    
    sync_resource_allocation = dict()
    
    for key in system.switches:
        switch = system.switches[key]
        for i in range(0, switch.current_nbr_ports):
            sync_resource_allocation[switch.ports[i].name] = list()
    for key in system.NIC_endpoints:
        endpoint = system.NIC_endpoints[key]
        sync_resource_allocation[endpoint.port.name] = list()

    return system, sync_resource_allocation


def create_industrial_hardware_system(r_generator = None, speed = "1Gbps", **kwargs):
    
    print("Create system: Industrial line topology")
    
    system = clm.CrossLayerModel(name='random_network_system')
    
    # ---- Init the network test setup ----
    # Init the switches
    system.add_switch("SW_0",4,speed)
    system.add_switch("SW_1",4,speed)
    system.add_switch("SW_2",4,speed)
    system.add_switch("SW_3",4,speed)
    system.add_switch("SW_4",4,speed)
    system.add_switch("SW_5",4,speed)
    system.add_switch("SW_6",4,speed)
    system.add_switch("SW_7",4,speed)

    # Connect the switches
    system.link_switch_to_switch(system.switches["SW_0"],system.switches["SW_1"])
    system.link_switch_to_switch(system.switches["SW_1"],system.switches["SW_2"])
    system.link_switch_to_switch(system.switches["SW_2"],system.switches["SW_3"])
    system.link_switch_to_switch(system.switches["SW_3"],system.switches["SW_4"])    
    system.link_switch_to_switch(system.switches["SW_4"],system.switches["SW_5"])
    system.link_switch_to_switch(system.switches["SW_5"],system.switches["SW_6"])
    system.link_switch_to_switch(system.switches["SW_6"],system.switches["SW_7"])
    
    
    # Init dummy endpoints
    system.add_NIC_endpoint('NIC_0_0',speed)
    system.add_NIC_endpoint('NIC_0_1',speed)
    system.add_NIC_endpoint('NIC_0_2',speed)
    system.add_NIC_endpoint('NIC_1_0',speed)
    system.add_NIC_endpoint('NIC_1_1',speed)
    system.add_NIC_endpoint('NIC_2_0',speed)
    system.add_NIC_endpoint('NIC_2_1',speed)
    system.add_NIC_endpoint('NIC_3_0',speed)    
    system.add_NIC_endpoint('NIC_3_1',speed)
    system.add_NIC_endpoint('NIC_4_0',speed)
    system.add_NIC_endpoint('NIC_4_1',speed)
    system.add_NIC_endpoint('NIC_5_0',speed)
    system.add_NIC_endpoint('NIC_5_1',speed)
    system.add_NIC_endpoint('NIC_6_0',speed)
    system.add_NIC_endpoint('NIC_6_1',speed)
    system.add_NIC_endpoint('NIC_7_0',speed)    
    system.add_NIC_endpoint('NIC_7_1',speed)
    system.add_NIC_endpoint('NIC_7_2',speed)
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_0"],system.switches["SW_0"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_1"],system.switches["SW_0"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_0_2"],system.switches["SW_0"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_1_0"],system.switches["SW_1"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_1_1"],system.switches["SW_1"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_2_0"],system.switches["SW_2"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_2_1"],system.switches["SW_2"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_3_0"],system.switches["SW_3"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_3_1"],system.switches["SW_3"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_4_0"],system.switches["SW_4"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_4_1"],system.switches["SW_4"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_5_0"],system.switches["SW_5"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_5_1"],system.switches["SW_5"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_6_0"],system.switches["SW_6"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_6_1"],system.switches["SW_6"])
    
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_7_0"],system.switches["SW_7"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_7_1"],system.switches["SW_7"])
    system.link_NIC_endpoint_to_switch(system.NIC_endpoints["NIC_7_2"],system.switches["SW_7"])
    
    
    sync_resource_allocation = dict()
    
    for key in system.switches:
        switch = system.switches[key]
        for i in range(0, switch.current_nbr_ports):
            sync_resource_allocation[switch.ports[i].name] = list()
    for key in system.NIC_endpoints:
        endpoint = system.NIC_endpoints[key]
        sync_resource_allocation[endpoint.port.name] = list()

    return system, sync_resource_allocation
    
