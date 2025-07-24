"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Definition of Cross Layer Model nodes.
"""


import sys
import os
import math

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))


from pycpa import model
from composed_object_analysis import model as composed_model


#--------------------------------------------------
# Cross-Layer Model Nodes
# --------------------------------------------------

class BaseNode(object):
    """ A Node class with the basic functions for other nodes """
    def __init__(self, name, **kwargs):
        self.name = name

        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return str(self.name)
    
    def __str__(self):
        return str(self.name).replace('\n', ' ')



# -----------------------------------------------------------
# --------------------- Runtime-Nodes -----------------------
# ----------------------------------------------------------- 

class Task(BaseNode):
    ''' A Task is the smallest schedulable entities, which is running on an Execution Units '''
    def __init__(self, name, priority, bcet = None, wcet = None, is_let = False, ethernet_stream = None, service = None, resource = None, event_source = None, **kwargs):
        super().__init__(name, **kwargs)

        # properties
        self.priority = priority
        self.wcet = wcet
        self.bcet = bcet
        self.is_let_task = is_let        

        # Cross references
        self.ethernet_stream = ethernet_stream
        self.service = service
        self.event_source = event_source # Task or event source
        self.resource = resource

        # --- pycpa element ---
        self.cpa_task = None
        self.cpa_bcrt = None
        self.cpa_wcrt = None

        

        assert ethernet_stream == None or service == None , "Assertion: Task " + name + "can not be in a service and in an ethernet stream!"

class ExecUnit(BaseNode):
    """ Provides processing time to tasks """

    def __init__(self, name, domain, scheduler="SPNPScheduler", **kwargs):
        super().__init__(name, **kwargs)
        self.scheduler = scheduler
        self.tasks = dict()  

        # --- domain ---
        # "network" or "ecu"
        self.domain = domain

        # --- pycpa model elements ---
        self.pycpa_resource = None

        # --- pycpa results ---
        self.load = None
        




class EthernetEventSource(BaseNode):
    """ Advanced Ethernet event source """
    def __init__(self, name,burst_period_ns, burst_size, intra_burst_period_ns, d_min, activation_load_byte, jitter_ns = 0, synchronous = True, offset_ns = 0, **kwargs):
        super().__init__(name, **kwargs)

        self.burst_period_ns = burst_period_ns
        self.intra_burst_period_ns = intra_burst_period_ns
        self.burst_size = burst_size
        self.offset_ns = offset_ns

        self.d_min = d_min
        self.activation_load_byte = activation_load_byte

        self.jitter_ns = jitter_ns
        self.synchronous = synchronous



# -----------------------------------------------------------
# --------------------- Hardware-Nodes ----------------------
# ----------------------------------------------------------- 


class Switch(BaseNode):

    def __init__(self,name, max_nbr_ports, Mbits = "1Gbps", **kwargs):
        super().__init__(name, **kwargs)
        self.Mbits = Mbits
        self.max_nbr_ports = max_nbr_ports
        self.current_nbr_ports = 0

        # Port describing arrays
        self.ports = [None] * max_nbr_ports 
        self.port_edge_keys = [None] * max_nbr_ports # Storage for edge keys
        self.port_names = [None] * max_nbr_ports # Own port names
        self.port_remote_names = [None] * max_nbr_ports # The name of the connected instances via this port
        self.exec_units = [None] * max_nbr_ports

        # ---- Timing Model Entities ----
        # pycpa Ethernet
        self.pycpa_ethernet_switch = None

        # ---- Omnetpp ----
        self.mac_address = None
        

    def add_port(self, clm_system, **kwargs):

        # Check if maximum port number has been reached
        if self.current_nbr_ports >= self.max_nbr_ports:
            raise Exception('Maximum port number of switch has been reached')

        # Init the port
        new_port_id = self.current_nbr_ports
        self.current_nbr_ports = self.current_nbr_ports + 1
        port_name = self.name + "_output_port" + str(new_port_id) # Naming (Example): SW1_output_port_1
        self.port_names[new_port_id] = port_name

        # Create the execution unit
        exec_unit = clm_system.add_exec_unit(port_name, "network", 'SPNPScheduler')
        self.exec_units[new_port_id] = exec_unit
        exec_unit_name = len(clm_system.exec_units)
        clm_system.exec_units[exec_unit_name] = exec_unit

        # Connect the execution unit to the Switch
        clm_system.map_switch_to_resource(self, exec_unit, **kwargs)

        # return the current port number
        return new_port_id

	
class Port(BaseNode):

    def __init__(self, name, Mbits, **kwargs):
        super().__init__(name, **kwargs)
        self.Mbits=Mbits

        self.tasks = dict()

        # ---- Timing Model Entities ----
        # pycpa ethernet
        self.pycpa_resource = None
        self.pycpa_tasks = dict()


        # ---- Quantification ----
        # pycpa_ethernet
        self.pycpa_result = None

        # ---- Omnetpp ----
        self.port_address = None
        





class NICEndpoint(BaseNode):

    def __init__(self, name, speed = "1Gbps", **kwargs):
        super().__init__(name, **kwargs)

        # The link speed
        self.speed = speed

        # Two Execution Units
        self.tx_exec = None
        self.rx_exec = None

        # The physical port
        self.port = None
        self.port_edge_key = None
        self.port_name = None
        
        # Name of the connected (remote) physical port
        self.port_remote_name = None

        # List of all starting and ending streams
        self.starting_streams = dict()
        self.ending_streams = dict()

        # ---- Timing Model Entities ----
        # pycpa Ethernet
        self.pycpa_ethernet_node = None

        # ---- Omnetpp ----
        self.mac_address = None
        self.participant_id = None


# ------------------------------------------------------------------------------------
# ---------------------- Network Simulation Helper - Components ----------------------
# ------------------------------------------------------------------------------------


class EthernetStream(BaseNode):
    def __init__(self,name, start_NIC_endpoint,switch_list,end_NIC_endpoint,priority,hyperperiod, **kwargs):
        ''' Unicast Ethernet stream over multiple switches '''
        super().__init__(name, **kwargs)

        self.priority = priority
        
        #self.start_exec_unit = start_exec_unit
        self.start_NIC_endpoint = start_NIC_endpoint
        self.switch_list = switch_list
        self.end_NIC_endpoint = end_NIC_endpoint
        #self.end_exec_unit = end_exec_unit

        # Input Model
        self.input_model = None
        self.hyperperiod = hyperperiod

        # Tobe filled at initialization
        self.task_list = []
        self.port_list = []

        # --- Analysis results / Quantization ---
        self.dependency_quantization = dict()

        # ---- Timing Model Entities ----
        # pycpa Ethernet
        self.pycpa_ethernet_hw_entity_list = []
        self.pycpa_ethernet_port_list      = []
        self.pycpa_ethernet_task_list      = []
        self.pycpa_path = None

        # ---- Omnetpp ----
        self.global_stream_id = None
        self.writer_entity_id = None
        self.reader_entity_id = None

        # ---- Local quantification results ----
        
        self.sync_omnet_min_latency = None
        self.sync_omnet_max_latency = None
        self.sync_omnet_mean_latency = None
        
        self.sporadic_omnet_min_latency = None
        self.sporadic_omnet_max_latency = None
        self.sporadic_omnet_mean_latency = None
        
        self.sync_pycpa_ethernet_wcrt = None
        
        self.sporadic_pycpa_ethernet_wcrt = None
        
        self.comp_pycpa_ethernet_wcrt = None
        
        
        
        # Distance
        self.stream_distance = dict() 
        self.stream_nbr_ways = dict() 

        # pycpa
        self.path_latency = None
        self.wc_sample_latency = None

        # The "count-weight" to another stream
        self.dependency_count = dict()

    def list_hops(self):

        ret_string = str(self.start_NIC_endpoint)
        for i in range(0,len(self.switch_list)):
            ret_string = ret_string + " -> " + str(self.switch_list[i])
        ret_string = ret_string + " -> " + str(self.end_NIC_endpoint)

        return ret_string


    def get_max_bytes_per_package(self):
            
        if isinstance(self.input_model, StreamInputModel):
            return self.input_model.activation_load_byte
        elif isinstance(self.input_model, DDSStreamInputModel):
            return self.input_model.activation_load_byte
        else:
            print("Error: No valid Input model specified for stream")
            sys.exit()


    def create_sample_event_model(self, synchronous, composed, data_rate = 0):
        if not isinstance(self.input_model, DDSStreamInputModel):
            print("Error: Stream model should be of type DDSStreamInputModel")
            sys.exit()
            
        if self.input_model.synchronous == True and synchronous:
            
            if composed:
                assert data_rate > 0
                return composed_model.SyncComposedEventModel(self.hyperperiod, self.input_model.burst_period_ns, self.input_model.jitter, self.input_model.offset_ns, self.input_model.sample_size_byte, data_rate)
           # else:
           #     return sync_model.SyncSampleEventModel(self.hyperperiod, self.input_model.burst_period_ns, self.input_model.fragment_period_ns , self.input_model.number_of_fragments, self.input_model.jitter, self.input_model.offset_ns)
        else:
            return composed_model.SampleEventModel(self.input_model.burst_period_ns, self.input_model.number_of_fragments, self.input_model.fragment_period_ns ,  jitter=self.input_model.jitter)
        
    def create_pjd_event_model(self,period,jitter,d_min):
        if not isinstance(self.input_model, StreamInputModel):

            model.PJdEventModel(self,period,jitter,d_min)

            print("Error: Stream model should be of type StreamInputModel")
            sys.exit()
        
        print("Not implemented yet")
        sys.exit()
            


class StreamInputModel(BaseNode):
    def __init__(self,name,burst_period_ns,burst_size, d_min, activation_load_byte, jitter = 0, **kwargs):
        super().__init__(name, **kwargs)

        # ----> Timing
        # Inter Burst
        self.burst_period_ns = burst_period_ns
        # Intra Burst
        self.d_min = d_min
        self.jitter = jitter
        
        # ----> Load
        # Number of activations in bursts
        self.burst_size = burst_size
        # Load of a single activation
        self.activation_load_byte = activation_load_byte

        # Corresponding EthernetEventSource
        self.ethernet_event_source = None

        # ---- Timing Model Entities ----
        # pycpa Ethernet
        self.pycpa_event_model = None


    def params(self):
        print("P = " + str(self.burst_period_ns))
        print("N = " + str(self.burst_size))
        print("J = " + str(self.jitter))
        print("d = " + str(self.d_min))
        print("l = " + str(self.activation_load_byte))

class DDSStreamInputModel(StreamInputModel):
    def __init__(self,name,sample_size_byte, sample_period_ns, fragment_size_byte, fragment_period_ns, min_fragment_distance_ns, jitter=0 , dds_protocol_overhead=0, synchronous = False,offset_ns=0, **kwargs):

        # Number of burst activations
        self.number_of_fragments = math.ceil(sample_size_byte/fragment_size_byte)
        if sample_size_byte < fragment_size_byte:
             assert self.number_of_fragments == 1
             
             
        self.fragment_size_byte = fragment_size_byte
        if sample_size_byte <= 1500 and self.fragment_size_byte >= sample_size_byte:
            self.fragment_size_byte = sample_size_byte
        
            
        self.activation_load_byte = self.fragment_size_byte + dds_protocol_overhead

        assert self.activation_load_byte <= 1500 , "Assertion: DDS Stream model " + name + ": Specified load exeeds packet size."

        super().__init__( name, sample_period_ns, self.number_of_fragments, min_fragment_distance_ns, self.activation_load_byte, jitter,  **kwargs)

        # ---> Object parameters
        # Object Size in Byte
        self.sample_size_byte = sample_size_byte
        # ns object Period
        self.sample_period_ns = sample_period_ns
        self.fragment_period_ns = fragment_period_ns
        self.offset_ns = offset_ns
        self.synchronous = synchronous
      
        
        # Fragment Period in Byte
        self.min_fragment_distance_ns = min_fragment_distance_ns
        # The DDS overhead per fragment message
        self.dds_protocol_overhead = dds_protocol_overhead

        # Synchronization and Stack input
        self.jitter = jitter

        # Corresponding ethernet event source
        self.ethernet_event_source = None

        # Corresponding (N)ACK backchannel stream
        self.nack_stream = None





