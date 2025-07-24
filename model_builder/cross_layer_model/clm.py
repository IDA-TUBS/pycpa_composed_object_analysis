"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Cross Layer Model to represent an Ethernet System.
"""



# --- Add module paths ---
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# --- dependency analysis imports ---
from model_builder.cross_layer_model import clm_edges as ce
from model_builder.cross_layer_model import clm_nodes as cn

# --- timing analysis imports ---
from model_builder import pycpa_ethernet_exporter
import networkx as nx

class CrossLayerModel:

    def __init__(self,name='', **kwargs):
        self.name = name

        self.hyperperiod = None

        # cross layer model graph structure
        self.Graph = nx.MultiDiGraph()


         # ---- Export ----
        self.pycpa_sync_ethernet_model = None

        # run-time
        self.tasks = dict()
        self.ethernet_event_sources = dict()
        self.exec_units = dict()

        # hardware
        self.switches = dict()
        self.NIC_endpoints = dict()

        # network setup
        self.ethernet_streams = dict()
        self.stream_input_models = dict()

        for k, v in kwargs.items():
            setattr(self, k, v)



    # ---------------------------------------------------------------------------------------------
    # ----------------------------------------- add nodes -----------------------------------------
    # ---------------------------------------------------------------------------------------------

    # --- Runtime ---
    def add_task(self, name, priority, ethernet_stream = None, service = None,resource = None, event_source = None, **kwargs):
        task = cn.Task(name, priority, ethernet_stream = ethernet_stream, service = service, resource=resource, event_source = None, **kwargs)
        self.tasks[name] = task
        self.Graph.add_node(task, **kwargs)
        return task

    def add_exec_unit(self, name, domain, scheduler, **kwargs):
        exec_unit = cn.ExecUnit(name, domain, scheduler, **kwargs)
        self.exec_units[name] = exec_unit
        self.Graph.add_node(exec_unit, **kwargs)
        return exec_unit


    def add_ethernet_event_source(self, name, max_obj_B, obj_P, max_frag_B, frag_P, J, **kwargs):
        ethernet_event_source = cn.EthernetEventSource(name, max_obj_B, obj_P, max_frag_B, frag_P, J, **kwargs)
        self.ethernet_event_sources[name] = ethernet_event_source
        self.Graph.add_node(ethernet_event_source, **kwargs)
        return ethernet_event_source


    # --- Hardware ---
    def add_switch(self, name ,max_nbr_ports = 4, Mbits = "100Mbps",**kwargs):
        sw = cn.Switch(name, max_nbr_ports, Mbits, **kwargs)
        self.switches[name] = sw
        self.Graph.add_node(sw,**kwargs)
        return sw

    def add_NIC_endpoint(self, name, Mbits = "100Mbps", **kwargs):
        ''' Always in full duplex with two execution units'''

        # Create the NIC and add the resources to the dictionary
        NIC_endpoint = cn.NICEndpoint(name, Mbits, **kwargs)
        self.NIC_endpoints[name] = NIC_endpoint

        # Create the resources
        NIC_endpoint.tx_exec = self.add_exec_unit(name + "_tx_exec", "network", 'SPNPScheduler')
        NIC_endpoint.rx_exec = self.add_exec_unit(name + "_rx_exec", "network", 'SPNPScheduler')

        self.map_endpoint_to_resource(NIC_endpoint, NIC_endpoint.tx_exec, **kwargs)
        self.map_endpoint_to_resource(NIC_endpoint, NIC_endpoint.rx_exec, **kwargs)

        # Add the dummy to the graph
        self.Graph.add_node(NIC_endpoint, **kwargs)
        return NIC_endpoint


    # ---- Network Constructs ----
    def add_ethernet_stream(self, name, start_NIC, switch_list, end_NIC, priority, hyperperiod, **kwargs):
        # Check for validity
        if not len(switch_list) > 0:
            raise Exception("Switch list of Ethernet Stream is empty!")
            sys.exit()

        ethernet_stream = cn.EthernetStream(name, start_NIC, switch_list, end_NIC, priority, hyperperiod, **kwargs)
        self.ethernet_streams[name] = ethernet_stream

        # Add the stream to the start endpoint
        start_NIC.starting_streams[name] = ethernet_stream
        end_NIC.ending_streams[name] = ethernet_stream


        # First initialize the tasks of the start NIC and add them to the execution units
        task_nbr = 0
        start_task = self.add_task(priority = priority,name = name +"_T_"+ str(task_nbr), ethernet_stream = ethernet_stream)
        task_nbr = task_nbr + 1
        ethernet_stream.task_list.append(start_task)
        ethernet_stream.port_list.append(start_NIC.port)
        self.map_task_to_exec_unit(start_task,start_NIC.tx_exec);
        start_NIC.port.tasks[start_task.name] = start_task.name
        
        
        # Then add the tasks along the ethernet output ports
        for i in range(0, len(switch_list)-1):
            switch_1 = switch_list[i]
            switch_2 = switch_list[i+1]          

            # Get the relevant port
            for k in range(0, switch_1.current_nbr_ports):
                if switch_1.port_remote_names[k] == switch_2.name:
                    switch_output_port_task = self.add_task(name + "_T_" + str(task_nbr), priority, ethernet_stream = ethernet_stream)
                    task_nbr = task_nbr+1
                    ethernet_stream.task_list.append(switch_output_port_task)
                    ethernet_stream.port_list.append(switch_1.ports[k])
                    self.map_task_to_exec_unit(switch_output_port_task,switch_1.exec_units[k])
                    switch_1.ports[k].tasks[switch_output_port_task.name] = switch_output_port_task
                    break


        # Create the task between the last switch and the end NIC
        last_switch = switch_list[len(switch_list)-1]
        for i in range(0, last_switch.current_nbr_ports):
            if last_switch.port_remote_names[i] == end_NIC.name:
                switch_output_port_task = self.add_task(name + "_T_" + str(task_nbr), priority, ethernet_stream = ethernet_stream)
                task_nbr = task_nbr+1
                ethernet_stream.task_list.append(switch_output_port_task)
                ethernet_stream.port_list.append(last_switch.ports[i])
                self.map_task_to_exec_unit(switch_output_port_task, last_switch.exec_units[i])
                last_switch.ports[i].tasks[switch_output_port_task.name] = switch_output_port_task
                break


        # Create the task on the end EU
        end_task = self.add_task(name + "_T_" + str(task_nbr), priority, ethernet_stream = ethernet_stream)
        task_nbr = task_nbr+1
        ethernet_stream.task_list.append(end_task) 
        self.map_task_to_exec_unit(end_task,end_NIC.rx_exec);

        # 5th Connect the tasks
        for i in range(0,len(ethernet_stream.task_list)-1):
            self.link_task_precedence(ethernet_stream.task_list[i],ethernet_stream.task_list[i+1])
       
        return ethernet_stream



    # ---- Descriptive ----
    def add_stream_input_model(self,name,burst_period_ns, burst_size_byte, minimum_distance_ns, activation_load_byte, jitter_ns = 0, offset_ns= 0, **kwargs):
        stream_input_model = cn.StreamInputModel(name, burst_period_ns, burst_size_byte, minimum_distance_ns, activation_load_byte, jitter_ns, **kwargs)
        self.stream_input_models[name] = stream_input_model
        self.Graph.add_node(stream_input_model, **kwargs)

        # Add a corresponding EthernetEventSource
        stream_input_model.ethernet_event_source = self.add_ethernet_event_source("EthSrc_" + name, burst_period_ns, burst_size_byte, minimum_distance_ns, activation_load_byte, jitter_ns, offset_ns, **kwargs)
        edge = self.map_stream_input_model_to_ethernet_event_source(stream_input_model,stream_input_model.ethernet_event_source)

        return stream_input_model

    def add_dds_stream_input_model(self, name,sample_size_byte, sample_period_ns, fragment_size_byte, fragment_period_ns, min_fragment_distance_ns, jitter_ns=0 , dds_protocol_overhead=0, synchronous = False, offset_ns=0,  **kwargs):
        dds_stream_input_model = cn.DDSStreamInputModel(name,sample_size_byte, sample_period_ns, fragment_size_byte, fragment_period_ns, min_fragment_distance_ns, jitter_ns   , dds_protocol_overhead, synchronous, offset_ns, **kwargs)
        self.stream_input_models[name] = dds_stream_input_model
        self.Graph.add_node(dds_stream_input_model, **kwargs)
        # Add a corresponding EthernetEventSource
        dds_stream_input_model.ethernet_event_source = self.add_ethernet_event_source("DDSEthSrc_" + name, sample_period_ns, dds_stream_input_model.number_of_fragments, fragment_period_ns, min_fragment_distance_ns, dds_stream_input_model.activation_load_byte,jitter_ns=jitter_ns, synchronous=synchronous, offset_ns = offset_ns)
        edge = self.map_dds_stream_input_model_to_ethernet_event_source(dds_stream_input_model, dds_stream_input_model.ethernet_event_source)

        return dds_stream_input_model

    # -------------------------------------------------------------------------------------------------
    # ------------------------------------------ link nodes -------------------------------------------
    # -------------------------------------------------------------------------------------------------



    def link_task_precedence(self, task_1, task_2, **kwargs):

        assert isinstance(task_1, cn.Task)
        assert isinstance(task_2, cn.Task)

        edge_key = ce.Link_TaskPrecedence(**kwargs)
        edge = self.Graph.add_edge(task_1,task_2,edge_key,**kwargs)
        return edge_key


    # ---- Hardware ----

    def link_switch_to_switch(self, sw1, sw2, **kwargs):

        assert isinstance(sw1, cn.Switch)
        assert isinstance(sw2, cn.Switch)

        # First check for empty ports on both switches
        port_sw_1 = sw1.add_port(self)
        port_sw_2 = sw2.add_port(self)

	# Check Ethernet Connection
        if not sw1.Mbits == sw2.Mbits:
            raise Exception('ERROR while linking switches: Switches have incompatible Mbits!')

	# Check if both switches have empty ports
        if port_sw_1 == None or port_sw_2 == None:
            raise Exception('ERROR while linking switches: Switch has no free ports!')

        # Create Ethernet Connection
        edge_key = ce.Ethernet_Connection(sw1,sw2,**kwargs)
        sw1.port_edge_keys[port_sw_1] = edge_key
        sw2.port_edge_keys[port_sw_2] = edge_key
        sw1.port_remote_names[port_sw_1] = sw2.name
        sw2.port_remote_names[port_sw_2] = sw1.name
        sw1.ports[port_sw_1] = cn.Port("Port_" + str(port_sw_1) + "_" + sw1.name, sw1.Mbits)
        sw2.ports[port_sw_2] = cn.Port("Port_" + str(port_sw_2) + "_" + sw2.name, sw1.Mbits)

        # Add the Connection to the Graph
        edge = self.Graph.add_edge(sw1, sw2, edge_key, **kwargs)

        return edge_key





    def link_NIC_endpoint_to_switch(self, NIC_endpoint, switch, **kwargs):

        assert isinstance(NIC_endpoint, cn.NICEndpoint)
        assert isinstance(switch, cn.Switch)

	# Check Ethernet Connection
        if not switch.Mbits == NIC_endpoint.speed:
            raise Exception('ERROR while linking EDE to Switch: Switch and EDE have incompatible Mbits!')

        switch_port = switch.add_port(self)
        
        # Create the Ethernet Connection
        edge_key = ce.Ethernet_Connection(NIC_endpoint,switch,**kwargs)
        switch.port_edge_keys[switch_port] = edge_key
        switch.ports[switch_port] = cn.Port("Port_" + str(switch_port) + "_" + switch.name, switch.Mbits)
        switch.port_remote_names[switch_port] = NIC_endpoint.name
        NIC_endpoint.port = cn.Port("Port_" + NIC_endpoint.name, switch.Mbits)
        NIC_endpoint.port_edge_key = edge_key
        NIC_endpoint.port_name = NIC_endpoint.name
        NIC_endpoint.port_remote_name = switch.name

        # Add edge to graph
        edge1 = self.Graph.add_edge(NIC_endpoint,switch,edge_key,**kwargs)




    # -------------------------------------------------------------------------------------------------
    # ------------------------------------------- map nodes -------------------------------------------
    # -------------------------------------------------------------------------------------------------

    def map_task_to_exec_unit(self, task, exec_unit, **kwargs):

        assert isinstance(task, cn.Task)
        assert isinstance(exec_unit, cn.ExecUnit)

        exec_unit.tasks[task.name] = task

        edge =ce.Mapping_TaskToExecUnit(**kwargs)
        task.resource = exec_unit
        self.Graph.add_edge(task, exec_unit, edge, **kwargs)

        return edge

    def map_switch_to_resource(self, switch, exec_unit, **kwargs):

        assert isinstance(switch, cn.Switch)
        assert isinstance(exec_unit, cn.ExecUnit)

        edge_key = ce.Mapping_SwitchToExecUnit(**kwargs)
        edge = self.Graph.add_edge(switch,exec_unit,edge_key,**kwargs)
        return edge_key

    def map_endpoint_to_resource(self, endpoint, exec_unit, **kwargs):

        assert isinstance(endpoint, cn.NICEndpoint)
        assert isinstance(exec_unit, cn.ExecUnit)

        edge_key = ce.Mapping_NICEndpointToExecUnit(**kwargs)
        edge = self.Graph.add_edge(endpoint,exec_unit,edge_key,**kwargs)
        return edge_key

    def map_ethernet_event_source_to_ethernet_stream(self, ethernet_event_source, ethernet_stream, **kwargs):

        assert isinstance(ethernet_event_source, cn.EthernetEventSource)
        assert isinstance(ethernet_stream, cn.EthernetStream)

        edge = ce.Mapping_EthernetEventSourceToEthernetStream(**kwargs)
        self.Graph.add_edge(ethernet_event_source, ethernet_stream, edge, **kwargs)
        return edge


    def map_stream_input_model_to_ethernet_event_source(self, stream_input_model, ethernet_event_source, **kwargs):

        assert isinstance(stream_input_model, cn.StreamInputModel)
        assert isinstance(ethernet_event_source, cn.EthernetEventSource)

        edge = ce.Mapping_StreamInputModelToEthernetEventSource(**kwargs)
        self.Graph.add_edge(stream_input_model, ethernet_event_source, **kwargs)
        return edge

    def map_dds_stream_input_model_to_ethernet_event_source(self, dds_stream_input_model, ethernet_event_source, **kwargs):

        assert isinstance(dds_stream_input_model, cn.DDSStreamInputModel)
        assert isinstance(ethernet_event_source, cn.EthernetEventSource)

        edge = ce.Mapping_DDSStreamInputModelToEthernetEventSource(**kwargs)
        self.Graph.add_edge(dds_stream_input_model, ethernet_event_source, **kwargs)
        return edge

    def map_task_to_ethernet_event_source(self,task, ethernet_event_source, **kwargs):

        assert isinstance(ethernet_event_source, cn.EthernetEventSource)
        assert isinstance(task, cn.Task)

        edge = ce.Mapping_TaskToEthernetEventSource(**kwargs)
        self.Graph.add_edge(task,ethernet_event_source, edge, **kwargs)
        return edge

    def map_stream_input_model_to_ethernet_stream(self,stream_input_model, ethernet_stream, **kwargs):
        edge = ce.Mapping_StreamInputModelToEthernetStream(**kwargs)

        assert isinstance(stream_input_model, cn.StreamInputModel)
        assert isinstance(ethernet_stream, cn.EthernetStream)

        ethernet_stream.input_model = stream_input_model

        task = ethernet_stream.task_list[0]

        # get event source
        ethernet_event_source = stream_input_model.ethernet_event_source
        self.map_task_to_ethernet_event_source(task,ethernet_event_source)

        return edge








    # -------------------------------------------------------------------------------------------------
    # --------------------------------------------- Export --------------------------------------------
    # -------------------------------------------------------------------------------------------------


    def pycpa_ethernet_export(self, synchronous, composed = False):
        exporter = pycpa_ethernet_exporter.pyCPAEthernetExporter(self, synchronous, composed = composed)
        exporter.delete_existing_pycpa_content_from_clm()
        self.pycpa_sync_ethernet_model = exporter.export_ethernet_network_to_pycpa_model()
        
        return exporter


    
























































