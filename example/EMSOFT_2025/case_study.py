"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Example to initialize, configure and analyze different systems.
Related to the Experiemnts of EMSOFT 2025 (Peeck et al.)
"""

import sys, os
import copy
import math
import time
import pandas as pd
import random
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from model_builder import random_system_generator
from model_builder import build_system_topologies as top
from model_builder.cross_layer_model import clm
from model_builder.cross_layer_model import clm_nodes as cn
    
last_value = 0
def generate_random_object_route(system, r_generator, end_nics):

    start_nic_id = r_generator.random_value_in_int_interval(0,len(system.NIC_endpoints)-1)
    start_nic = list(system.NIC_endpoints.values())[start_nic_id]
    global last_value
    random_value = prn_generator.random_value_in_int_interval(0,1)
    if len(end_nics) == 1:
        end_nic = end_nics[0]
    else:
        if last_value == 0:
            random_value = 1
            last_value = 1
        else:
            last_value = 0
            random_value = 0
        if random_value == 0:
            end_nic = end_nics[0]
        elif random_value == 1:
            end_nic = end_nics[1]
    
    while True:
        start_nic_id = r_generator.random_value_in_int_interval(0,len(system.NIC_endpoints)-1)
        start_nic = list(system.NIC_endpoints.values())[start_nic_id]
        if not start_nic in end_nics:
            break

    random_stream = random_system_generator.generate_random_shortest_stream(r_generator, system, start_nic, end_nic)
  
  
    return random_stream


def generate_random_route(system, r_generator, limitation = True):

    start_nic_id = r_generator.random_value_in_int_interval(0,len(system.NIC_endpoints)-1)
    end_nic_id = r_generator.random_value_in_int_interval(0,len(system.NIC_endpoints)-1)
    
    
    
    if False:
        no_end_nics = [system.NIC_endpoints["NIC_HR_1"],system.NIC_endpoints["NIC_HR_2"]]
        while True:
            end_nic_id = r_generator.random_value_in_int_interval(0,len(system.NIC_endpoints)-1)
            end_nic = list(system.NIC_endpoints.values())[end_nic_id]
            
            if not end_nic in no_end_nics:
                break
        
        while end_nic_id == start_nic_id:
            start_nic_id = r_generator.random_value_in_int_interval(0,len(system.NIC_endpoints)-1)
        



    
    while end_nic_id == start_nic_id:
        end_nic_id = r_generator.random_value_in_int_interval(0,len(system.NIC_endpoints)-1)

    start_nic = list(system.NIC_endpoints.values())[start_nic_id]
    end_nic   = list(system.NIC_endpoints.values())[end_nic_id]
    
    random_stream = random_system_generator.generate_random_shortest_stream(r_generator, system, start_nic, end_nic)
   
    return random_stream


def add_control_stream(system, prn_generator,control_stream_number):

    route = generate_random_route(system, prn_generator, limitation = True)
    
    period = 20*1000*1000
    
    offset = prn_generator.random_value_in_int_interval(0,period)
    
    stream_name = "ControlStream" + str(control_stream_number)
    control_stream = system.add_ethernet_stream(stream_name, route[0],route[1:len(route)-1],route[len(route)-1],0,system.hyperperiod) 
        
    
        
    # 2 types:
    # Type 1: 20Hz 1frame J=5ms dmin = 200us
    # Type 2: 10Hz 5frame J=5ms dmin = 200us
    random_value = prn_generator.random_value_in_int_interval(0,1)
        
    if random_value == 0: # Type 1
        control_input_model = system.add_dds_stream_input_model("control_stream_"+str(control_stream_number),1*512, period, 1500, 120*1000,0, jitter_ns=000*1000,dds_protocol_overhead=0, offset_ns = offset, synchronous = False)
    else: # Type 2
        control_input_model = system.add_dds_stream_input_model("control_stream_"+str(control_stream_number),1*512, period, 1500, 120*1000,0, jitter_ns=000*1000,dds_protocol_overhead=0, offset_ns = offset, synchronous = False)
     
    system.map_stream_input_model_to_ethernet_stream(control_input_model, system.ethernet_streams[stream_name])
    return control_stream

    
def get_ports_from_route(system, route):

    port_list = list()

    for k in range(0,len(route)-1):
    
        hop = route[k]
        if isinstance(hop, cn.NICEndpoint):
            port_list.append(hop.port)
            
        if isinstance(hop, cn.Switch):
        
            # Get next hop
            next_switch = route[k+1]
        
            for l in range(0, len(hop.port_remote_names)):
                remote_entity = hop.port_remote_names[l]

                if str(remote_entity) == str(next_switch):
                    port_list.append(hop.ports[l])
                    
    return port_list
    
    
def add_object_stream(system, prn_generator, object_stream_number, sync_resource_allocation,data_rate, endpoint_names, toggle_random, _jitter = 500*1000):


    end_nics = list()
    
    for end_nic_name in endpoint_names:
        end_nics.append(system.NIC_endpoints[end_nic_name])
    
        
    route = generate_random_object_route(system, prn_generator, end_nics)
    ports = get_ports_from_route(system,route)
    stream_name = "ObjectStream" + str(object_stream_number)
    object_stream = system.add_ethernet_stream(stream_name, route[0],route[1:len(route)-1],route[len(route)-1],1,system.hyperperiod) 
    
    
    
    sample_period = 40*1000*1000 # 25Hz
    if toggle_random:
        if object_stream_number % 2 == 0:
            sample_period = 50*1000*1000
        else:
            sample_period = 40*1000*1000
    
    duration = 3.2*1000*1000
    frame_duration = (1500*8*1000*1000*1000)/data_rate
    nbr_frames = math.ceil(duration/frame_duration)
    sample_size= 1500*nbr_frames
    
    resulting_duration = (sample_size * 8 * 1000*1000*1000)/data_rate
    
    
    minmax_overlap_value = 0
    minmax_offset_value  = None
    minimum_hop_with_overlapping = 10
    
    guard_interval = 1200*1000
    
    for phi in range(0,sample_period,500*1000):
    
        add = int(random.uniform(0, 1)*sample_period)
        add = 0
        
        phi_add = (phi+add)%sample_period
    
        overlap = True
    
        current_minmax_overlap = None
        current_offset_value = None
        
        current_minimum_hop = 10
        hop_number = 0
    
        for port in ports:
        
            hop_number += 1
            
            for n in range(0,int(system.hyperperiod/sample_period)):

                interval = [-guard_interval + phi_add + n*sample_period, phi_add + n*sample_period +  resulting_duration + guard_interval]
                
                 # add margen to left and right
                current_port_allocation = sync_resource_allocation[port.name]
                
                # First sum up the overlap of the port
                _sum = 0
                for i in range(0,len(current_port_allocation)):
                    # Calculate the overlap
                    comp_interval = current_port_allocation[i]
                    comp_start = comp_interval[0]
                    comp_end   = comp_interval[1]
                
                    interval_start = interval[0]
                    interval_end   = interval[1]                  
                
                    if interval_end <= comp_start or comp_end <= interval_start:
                        continue
                    if interval_end >= comp_start:
                        _sum = _sum + interval_end - comp_start
                        assert _sum >= 0
                    elif comp_end >= interval_start:           
                        _sum = _sum + comp_end - interval_start    
                        assert _sum >= 0
                
                if _sum > 0 and hop_number < current_minimum_hop:
                    current_minimum_hop = hop_number
                
                if current_minmax_overlap == None:
                    current_minmax_overlap = _sum
                    current_offset_value = phi_add
                    continue
                    
                if current_minmax_overlap < _sum:
                    current_minmax_overlap = _sum
                    current_offset_value = phi_add
                    
                    
        if minmax_offset_value == None:
            minmax_offset_value = current_offset_value
            minimum_hop_with_overlapping = current_minimum_hop
            minmax_overlap_value = current_minmax_overlap
            continue 
            
        if (current_minmax_overlap <= minmax_overlap_value and current_minimum_hop >= minimum_hop_with_overlapping ) or current_minimum_hop >= minimum_hop_with_overlapping:
        
        
            minmax_overlap_value = current_minmax_overlap
            minmax_offset_value = current_offset_value
            if current_minmax_overlap == 0:
                overlap = False
        
        if not overlap:
            break;
            
                    
    # Add the resulting offset configuration    
    packet_time_shift = 0
    for port in ports:

        for n in range(0,int(system.hyperperiod/sample_period)):
        
            interval = [minmax_offset_value + n*sample_period,  minmax_offset_value + n*sample_period +  nbr_frames * frame_duration] 

            sync_resource_allocation[port.name].append(interval)         
                    

    
        
    
    fragment_period = (1500*8)*(1000*1000*1000/data_rate)

    if toggle_random:
        minmax_offset_value = prn_generator.random_value_in_int_interval(0,sample_period)
    
    object_input_model = system.add_dds_stream_input_model("object_stream_"+str(object_stream_number),sample_size, sample_period, 1500, fragment_period ,0, jitter_ns=_jitter, dds_protocol_overhead=0, synchronous = True, offset_ns = minmax_offset_value)
    system.map_stream_input_model_to_ethernet_stream(object_input_model, system.ethernet_streams[stream_name])
    
    return object_stream
    
    
    
    
    

   
   
def EMSOFT_2025_running_example(system, data_rate, control_streams, object_streams):

    # Add control streams
    route = [system.NIC_endpoints["NIC_HL_2"], system.switches["SW_HL"],system.switches["SW_VL"],system.switches["SW_VR"],system.NIC_endpoints["NIC_VR_2"]]
    
    byte_size = 500
    period = 10*1000*1000
    jitter = 500*1000
    fragment_period = (byte_size*8)*(1000*1000*1000/data_rate)
    
    add_control_stream = True
    if add_control_stream:
        stream_name = "ControlStream" + str(1)
        control_stream = system.add_ethernet_stream(stream_name, route[0],route[1:len(route)-1],route[len(route)-1],0,system.hyperperiod) 
        control_input_model = system.add_dds_stream_input_model("control_stream_1",byte_size, period, 1500, fragment_period,0, jitter_ns=0, dds_protocol_overhead=0, offset_ns = 0, synchronous = False)
        control_streams[control_stream.name] = control_stream
        system.map_stream_input_model_to_ethernet_stream(control_input_model, system.ethernet_streams[stream_name])
        nbr_control_streams = 1
    else:
        nbr_control_streams = 0
    
    # Add Object streams
    route_1 = [system.NIC_endpoints["NIC_VL_2"], system.switches["SW_VL"],system.switches["SW_VR"],system.NIC_endpoints["NIC_VR_1"]] # Grün
    route_2 = [system.NIC_endpoints["NIC_VL_1"], system.switches["SW_VL"],system.switches["SW_VR"],system.NIC_endpoints["NIC_VR_2"]] # Gelb
    route_3 = [system.NIC_endpoints["NIC_HL_1"], system.switches["SW_HL"],system.switches["SW_VL"],system.switches["SW_VR"],system.NIC_endpoints["NIC_VR_2"]] # Blau
    route_4 = [system.NIC_endpoints["NIC_HR_1"], system.switches["SW_HR"],system.switches["SW_VR"],system.NIC_endpoints["NIC_VR_1"]] # Braun
    route_5 = [system.NIC_endpoints["NIC_HL_2"], system.switches["SW_HL"],system.switches["SW_VL"],system.NIC_endpoints["NIC_VL_1"]] # Rot
    
    jitter = 1000*1000 # 500us
    stream_name_1 = "ObjectStream1"
    stream_name_2 = "ObjectStream2"
    stream_name_3 = "ObjectStream3"
    stream_name_4 = "ObjectStream4"
    stream_name_5 = "ObjectStream5"
    object_stream_1 = system.add_ethernet_stream(stream_name_1, route_1[0],route_1[1:len(route_1)-1],route_1[len(route_1)-1],1,system.hyperperiod) 
    object_stream_2 = system.add_ethernet_stream(stream_name_2, route_2[0],route_2[1:len(route_2)-1],route_2[len(route_2)-1],1,system.hyperperiod) 
    object_stream_3 = system.add_ethernet_stream(stream_name_3, route_3[0],route_3[1:len(route_3)-1],route_3[len(route_3)-1],1,system.hyperperiod) 
    object_stream_4 = system.add_ethernet_stream(stream_name_4, route_4[0],route_4[1:len(route_4)-1],route_4[len(route_4)-1],1,system.hyperperiod) 
    object_stream_5 = system.add_ethernet_stream(stream_name_5, route_5[0],route_5[1:len(route_5)-1],route_5[len(route_5)-1],1,system.hyperperiod) 
    object_streams[object_stream_1.name] = object_stream_1
    object_streams[object_stream_2.name] = object_stream_2
    object_streams[object_stream_3.name] = object_stream_3
    object_streams[object_stream_4.name] = object_stream_4
    object_streams[object_stream_5.name] = object_stream_5
    
    
    offset_1 = 3*1000*1000
    offset_2 = 0*1000*1000
    offset_3 = 13*1000*1000
    offset_4 = 0*1000*1000
    offset_5 = 14*1000*1000
    
    
    sample_period = 100*1000*1000
    sample_size_1= int((0.006 * data_rate)/8)
    sample_size_2= int((0.008 * data_rate)/8)
    sample_size_3= int((0.002 * data_rate)/8)
    sample_size_4= int((0.005 * data_rate)/8)
    sample_size_5= int((0.004 * data_rate)/8)
    #print(sample_size_1)
    
    frame_duration = 1500*8 *(1000*1000*1000/data_rate)
   # print(frame_duration)
        
    object_input_model_1 = system.add_dds_stream_input_model(stream_name_1,sample_size_1, sample_period, 1500, frame_duration ,0, jitter_ns=jitter,dds_protocol_overhead=0, synchronous = True, offset_ns = offset_1)
    object_input_model_2 = system.add_dds_stream_input_model(stream_name_2,sample_size_2, sample_period, 1500, frame_duration ,0, jitter_ns=jitter,dds_protocol_overhead=0, synchronous = True, offset_ns = offset_2)
    object_input_model_3 = system.add_dds_stream_input_model(stream_name_3,sample_size_3, sample_period, 1500, frame_duration ,0, jitter_ns=jitter,dds_protocol_overhead=0, synchronous = True, offset_ns = offset_3)
    object_input_model_4 = system.add_dds_stream_input_model(stream_name_4,sample_size_4, sample_period, 1500, frame_duration ,0, jitter_ns=jitter,dds_protocol_overhead=0, synchronous = True, offset_ns = offset_4)
    object_input_model_5 = system.add_dds_stream_input_model(stream_name_5,sample_size_5, sample_period, 1500, frame_duration ,0, jitter_ns=jitter,dds_protocol_overhead=0, synchronous = True, offset_ns = offset_5)
    system.map_stream_input_model_to_ethernet_stream(object_input_model_1, system.ethernet_streams[stream_name_1])
    system.map_stream_input_model_to_ethernet_stream(object_input_model_2, system.ethernet_streams[stream_name_2])
    system.map_stream_input_model_to_ethernet_stream(object_input_model_3, system.ethernet_streams[stream_name_3])
    system.map_stream_input_model_to_ethernet_stream(object_input_model_4, system.ethernet_streams[stream_name_4])
    system.map_stream_input_model_to_ethernet_stream(object_input_model_5, system.ethernet_streams[stream_name_5])
    
    nbr_object_streams = 5
    
    return nbr_control_streams, nbr_object_streams

    
    



if __name__ == "__main__":
    
    #  Parse the experiment value
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment",type=int, default=1,
            help="Filename of the .csv file")
    args = parser.parse_args()
    experiment = args.experiment
    
    # Experiment 1: EMSOFT 2025 running paper example
    # Experiemnt 2: EMSOFT 2025 composed analysis automotive results
    # Experiment 3: EMSOFT 2025 composed analysis industrial line topology results
    # Experiment 4: EMSOFT 2025 composed analysis industrial star topology results
    
    assert experiment == 1 or experiment == 2 or experiment == 3 or experiment == 4, "Invalid experiment input. Number between 1 and 3 is required"
    configure = None
    
    
    
    # ---- Configure the experiments	----
    # Analysis processing time
    if experiment == 1:
        configure = "running_paper_example"
    
    elif experiment == 2:
        configure = "composed_automotive_ring"

    elif experiment == 3:
        configure = "composed_industrial_line"
    
    elif experiment == 4:
        configure = "composed_industrial_star"
    
    print("Configured experiment: " + str(configure))
        
        
    
        
        
    
    ###################################################################
    ########################## Configuration ##########################
    ###################################################################
    
    # Configure the hyperperiod
    hyperperiod = 1000*1000*1000
    
    # Same data rate for all streams
    data_rates = [100*1000*1000, 1000*1000*1000, 10*1000*1000*1000]
    
    # Other parameters
    toggle_random = False
       
    # Add Streams to the system
    nbr_control_streams = 40
    nbr_static_object_streams = 1
    nbr_object_stream_creation_iterations = 18
    
    # Endpoin names
    endpoint_names = []
    
    
        
        
    # Configure the jitter
    jitter_factors = [500*1000]
    
        
    # default seed
    seed= 1
    
    
    

    
    if configure == "running_paper_example":
        data_rates = [1000*1000*1000] # 1Gbps
        hyperperiod = 200*1000*1000
        nbr_control_streams = 0
        nbr_static_object_streams = 0
        nbr_object_stream_creation_iterations = 1
        
    elif configure == "composed_automotive_ring":
        seed = 1
        data_rates = [100*1000*1000, 1000*1000*1000, 10*1000*1000*1000]
        hyperperiod = 200*1000*1000
        nbr_control_streams = 40
        nbr_static_object_streams = 10
        nbr_object_stream_creation_iterations = 8
        endpoint_names = ["NIC_VR_1","NIC_VL_1"]
        
    elif configure == "composed_industrial_line":
        seed = 1241
        data_rates = [10*1000*1000*1000]
        hyperperiod = 80*1000*1000
        nbr_control_streams = 40
        nbr_static_object_streams = 10
        nbr_object_stream_creation_iterations = 8
        endpoint_names = ["NIC_5_0","NIC_2_0"]
        
    elif configure == "composed_industrial_star":
        seed = 5486
        data_rates = [10*1000*1000*1000]
        hyperperiod = 200*1000*1000
        nbr_control_streams = 40
        nbr_static_object_streams = 1
        nbr_object_stream_creation_iterations = 12
        toggle_random = True
        endpoint_names = ["NIC_0_0"]
        
    else:
        assert False, "Invalid configuration"
    
        
    ######################################################################
    ######################################################################
    
    # Initialize empty pandas frame for data collection# type: control or object streams
    data_frame_column = \
        ["nbr_object_streams",\
         "nbr_control_streams",\
         "stream_id",\
         "stream_name",\
         "type",\
         "start_nic",\
         "end_nic",\
         "sample_period",\
         "sample_size",\
         "fragment_size",\
         "nbr_of_fragments",\
         "jitter",\
         "data_rate",\
         "average_link_utilization",\
         "config_robustness",\
         "latency_composed_analysis",\
         "evaluation_type",\
         "latency_value","elapsed_time",\
         "elapsed_time_composed",\
         "offset"]
         
         
                    
    data_frame = pd.DataFrame(columns=data_frame_column)
    current_line_count = 0
    
    
    
    
    
    # ------------------------------------------------------------
    # ---------- Create the system and run the analysis ----------
    # ------------------------------------------------------------

    for data_rate in data_rates:
    
        # Streams that store analysis data
        control_streams = dict()
        object_streams    = dict()
        
        # Count stream types 
        object_stream_count = 0
        control_stream_count = 0
    
        # First create the systems, which depends on the data rate
        system = None
        if configure == "running_paper_example":
            system, sync_resource_allocation = top.create_automotive_ring_topology(speed = data_rate)
            system.hyperperiod = hyperperiod
            control_stream_count , object_stream_count = EMSOFT_2025_running_example(system, data_rate, control_streams, object_streams)

        if configure == "composed_automotive_ring":
            system, sync_resource_allocation = top.create_automotive_ring_topology(speed = data_rate)
            system.hyperperiod = hyperperiod

        if configure == "composed_industrial_line":
            system, sync_resource_allocation = top.create_industrial_hardware_system(speed = data_rate)
            system.hyperperiod = hyperperiod
            
        if configure == "composed_industrial_star":
            system, sync_resource_allocation = top.create_star_hardware_system(speed = data_rate)
            system.hyperperiod = hyperperiod
            
        system.save_directory = "./"
            
        
        # ---------- Generate the system --------------
        # Set back the seed, so that same stream routes are created the same every run
        prn_generator = random_system_generator.PseudoRandomGenerator(seed)
            
        # Add Control Streams
        for c in range(0,nbr_control_streams):
            control_stream = add_control_stream(system, prn_generator, control_stream_count)
            control_stream_count = control_stream_count + 1
            control_streams[control_stream.name] = control_stream 

        # Number of static Object Streams
        for i in range(0, nbr_static_object_streams):
                      
            object_stream = add_object_stream(system, prn_generator, object_stream_count, sync_resource_allocation, data_rate, endpoint_names, toggle_random)
            object_stream_count = object_stream_count + 1
            object_streams[object_stream.name] = object_stream
             
        # Add Object streams
        for i in range(0, nbr_object_stream_creation_iterations):
        
            # Debug
            print("\n")
            print("------ Current Setup ------")
            print("Data rate: " + str(data_rate))
            print("Iteration: " + str(i+1))
            print("Nbr of object streams: " + str(nbr_static_object_streams + (i+1)))
                    
                    
            # Add range streams
            if not configure == "running_paper_example":
                object_stream = add_object_stream(system, prn_generator, object_stream_count, sync_resource_allocation, data_rate, endpoint_names, toggle_random)
                object_stream_count = object_stream_count + 1
                object_streams[object_stream.name] = object_stream
                
                
            print("------------------------ Composed Ethernet Analysis ----------------------------")
                
            # ---- Synchronous analysis composed objects ----
            exporter = system.pycpa_ethernet_export(True, composed = True) # True: synchronous, False: sporadic
            #exporter.print_pycpa_ethernet_model(len(object_streams))
            start = time.time()
            exporter.run_ethernet_analysis(data_frame)
            end = time.time()
            elapsed_time_composed = end-start
                                      
                
                
            # ---- Collect and store data ----
            new_line = [None] * len(data_frame_column)
            new_line[0] = object_stream_count
            new_line[1] = control_stream_count
            new_line[14] = 0
                        
            for key in object_streams:
                object_stream = object_streams[key] 

                new_line[2] = object_stream.global_stream_id
                new_line[3] = object_stream.name
                new_line[4] = "object_stream"
                new_line[5] = object_stream.start_NIC_endpoint.name
                new_line[6] = object_stream.end_NIC_endpoint.name
                new_line[7] = object_stream.input_model.sample_period_ns
                new_line[8] = object_stream.input_model.sample_size_byte
                new_line[9] = object_stream.input_model.fragment_size_byte 
                new_line[10] = object_stream.input_model.number_of_fragments
                new_line[11] = object_stream.input_model.jitter
                new_line[12] = data_rate
                new_line[13] = 0.0
                    
                # Reference measures
                new_line[15] = object_stream.comp_pycpa_ethernet_wcrt
                    
                #new_line[23] = elapsed_time_single_packet
                new_line[19] = elapsed_time_composed
                new_line[20] = object_stream.input_model.offset_ns
                    

                new_line = copy.deepcopy(new_line)
                new_line[16] = "latency_composed_analysis"
                new_line[18] = elapsed_time_composed
                new_line[17] = object_stream.comp_pycpa_ethernet_wcrt
                new_row = pd.DataFrame([new_line], columns=data_frame.columns)
                data_frame = pd.concat([data_frame, new_row], ignore_index=True)
                current_line_count = current_line_count + 1
                    

                    

        
            # Store/overwrite the data frame after each round!
            if not os.path.exists("./output"):
                os.makedirs("./output")
    
            if configure == "running_paper_example":
                data_frame.to_csv("./output/analysis_running_paper_example.csv")
    
            if configure == "composed_automotive_ring":
                data_frame.to_csv("./output/analysis_automotive_ring_data_rates.csv")
                
            if configure == "composed_industrial_line":
                data_frame.to_csv("./output/analysis_industrial_line.csv")
                
            if configure == "composed_industrial_star":
                data_frame.to_csv("./output/analysis_industrial_star.csv")
                

   




















