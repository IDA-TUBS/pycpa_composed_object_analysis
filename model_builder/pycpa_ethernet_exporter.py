"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Exports the cross layer model into the pycpa model for analysis.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from model_builder.cross_layer_model import clm_edges as ce
from model_builder.cross_layer_model import clm_nodes as cn

from pycpa import schedulers
from pycpa import graph
from pycpa import model


from composed_object_analysis import analysis as composed_analysis
from composed_object_analysis import schedulers as composed_schedulers
from composed_object_analysis import model as composed_model
from composed_object_analysis import propagation as composed_propagation



from model_builder import network_resource_dependence

import math

INFINITY = float('inf')

def byte_to_sched_time(byte, speed):

    _speed = speed
    
    if speed == "10Gbps":
        _speed = 10* 1000*1000*1000
        
    if speed == "1Gbps":
        _speed = 1000*1000*1000

    if speed == "100Mbps":
        _speed = 100*1000*1000

    return ((byte*8)*(1000*1000*1000))/_speed


def speed(speed):

    _speed = speed
    
    if speed == "10Gbps":
        _speed = 10*1000*1000*1000
    
    if speed == "1Gbps":
        _speed = 1000*1000*1000

    if speed == "100Mbps":
        _speed = 100*1000*1000

    return _speed  





class pyCPAEthernetExporter:

    def __init__(self, cross_layer_model, synchronous, composed = False):

        self.cross_layer_model = cross_layer_model

        self.synchronous = synchronous
        
        self.composed_objects = composed

        # defaults
        if synchronous:
            if self.composed_objects:
                self.default_scheduler = composed_schedulers.SyncComposedObjectScheduler(cross_layer_model.hyperperiod)
            else:
                self.default_scheduler = schedulers.SyncSPPScheduler(cross_layer_model.hyperperiod)
        else: 
            self.default_scheduler = pycpa.SPNPScheduler()
        
        



    def delete_existing_pycpa_content_from_clm(self):
 
        # Streams
        for stream_key in self.cross_layer_model.ethernet_streams:
            stream = self.cross_layer_model.ethernet_streams[stream_key]

            stream.input_model.pycpa_event_model = None
            stream.pycpa_ethernet_hw_entity_list = []
            stream.pycpa_ethernet_port_list      = []
            stream.pycpa_ethernet_task_list      = []
            stream.pycpa_path = None

        # Switches
        for switch_key in self.cross_layer_model.switches:
            # Get the switch from the key
            switch = self.cross_layer_model.switches[switch_key]

            # Run through all ports of the switch
            for i in range(0, switch.current_nbr_ports):
                port = switch.ports[i]

                # Create the resources
                port.pycpa_resource = None
                port.pycpa_tasks = dict()

        # Endpoints
        for endpoint_key in self.cross_layer_model.NIC_endpoints:
            # Get the endpoint from key
            endpoint = self.cross_layer_model.NIC_endpoints[endpoint_key]
            # Create the resource
            port = endpoint.port
            endpoint.port.pycpa_resource = None
            




    def export_ethernet_network_to_pycpa_model(self):
   
        
        system = model.System()


        # ========== Create the resources ==========
        # First run through all switches and create the resources
        for switch_key in self.cross_layer_model.switches:
            # Get the switch from the key
            switch = self.cross_layer_model.switches[switch_key]

            # Run through all ports of the switch
            for i in range(0, switch.current_nbr_ports):
                port = switch.ports[i]
                
                # Create the resources
                if self.synchronous:
                
                    if self.composed_objects:
                        port.pycpa_resource = system.bind_resource(  composed_model.Resource(port.name, composed_schedulers.SyncComposedObjectScheduler(self.cross_layer_model.hyperperiod),speed(port.Mbits))   )
                    else:
                        port.pycpa_resource = system.bind_resource(model.Resource(port.name, schedulers.SyncSPPScheduler(self.cross_layer_model.hyperperiod)))
                else:
                    if self.composed_objects:
                        port.pycpa_resource = system.bind_resource(composed_model.Resource(port.name, ieee8021Q_analysis.IEEE8021QScheduler()))
                    else:
                        port.pycpa_resource = system.bind_resource(model.Resource(port.name, ieee8021Q_analysis.IEEE8021QScheduler()))
                    
        # Next run through all endpoints and create the resources
        for endpoint_key in self.cross_layer_model.NIC_endpoints:
            # Get the endpoint from key
            endpoint = self.cross_layer_model.NIC_endpoints[endpoint_key]
            # Create the resource
            port = endpoint.port
                # Create the resources
            if self.synchronous:
                if self.composed_objects:
                    port.pycpa_resource = system.bind_resource(composed_model.Resource(port.name, composed_schedulers.SyncComposedObjectScheduler(self.cross_layer_model.hyperperiod),speed(port.Mbits)))
                    
                else:
                    port.pycpa_resource = system.bind_resource(model.Resource(port.name, schedulers.SyncSPPScheduler(self.cross_layer_model.hyperperiod)))
            else:
                if self.composed_objects:
                    port.pycpa_resource = system.bind_resource(composed_model.Resource(port.name, ieee8021Q_analysis.IEEE8021QScheduler()))
                
                else:
                    port.pycpa_resource = system.bind_resource(model.Resource(port.name, ieee8021Q_analysis.IEEE8021QScheduler()))


        # ========== Create the streams ==========
        for stream_key in self.cross_layer_model.ethernet_streams:
            # Get the stream from key
            
            task_chain_id = 0
            
            stream = self.cross_layer_model.ethernet_streams[stream_key]
            # First get and configure the starting NIC
            stream.pycpa_ethernet_hw_entity_list.append(stream.start_NIC_endpoint)
            stream.pycpa_ethernet_port_list.append(stream.start_NIC_endpoint.port)

            _bcet = byte_to_sched_time(stream.get_max_bytes_per_package(), stream.start_NIC_endpoint.speed)
            _wcet = byte_to_sched_time(stream.get_max_bytes_per_package(), stream.start_NIC_endpoint.speed)

            
                                    
            if stream.input_model.synchronous and self.synchronous:
                if self.composed_objects:
                    current_task = composed_model.Task(stream.name + "_" + stream.start_NIC_endpoint.name + "_Task_" + str(task_chain_id), wcet = _wcet , bcet= _bcet, scheduling_parameter = stream.priority,OutEventModelClass=composed_propagation.SyncComposedPropagationEventModel, priority =stream.priority )
                else:
                    current_task = model.Task(stream.name + "_" + stream.start_NIC_endpoint.name + "_Task_" + str(task_chain_id), wcet = _wcet , bcet= _bcet, scheduling_parameter = stream.priority,OutEventModelClass=propagation.SyncPropagationEventModel, priority =stream.priority )
            else:
                if self.composed_objects:
                    current_task = composed_model.Task(stream.name + "_" + stream.start_NIC_endpoint.name + "_Task_" + str(task_chain_id), wcet = _wcet , bcet= _bcet, scheduling_parameter = stream.priority, priority =stream.priority)
                else:
                    current_task = model.Task(stream.name + "_" + stream.start_NIC_endpoint.name + "_Task_" + str(task_chain_id), wcet = _wcet , bcet= _bcet, scheduling_parameter = stream.priority, priority =stream.priority)
            task_chain_id += 1   
                        
            stream.pycpa_ethernet_task_list.append(current_task)
            stream.start_NIC_endpoint.port.pycpa_resource.bind_task(current_task)

            # Then add the Tasks for the switches except the last on (connected to a NIC endpoint)
            for i in range(0,len(stream.switch_list)-1):
                current_switch = stream.switch_list[i]
                next_switch = stream.switch_list[i+1]

                # Get the correct port towards the successive switch 
                for k in range(0,len(current_switch.port_remote_names)):
                    remote_entity = current_switch.port_remote_names[k]

                    if str(remote_entity) == str(next_switch):
    
                        # Then add the Task
                        stream.pycpa_ethernet_hw_entity_list.append(current_switch)
                        stream.pycpa_ethernet_port_list.append(current_switch.ports[k])

                        _bcet = byte_to_sched_time(stream.get_max_bytes_per_package(), current_switch.Mbits)
                        _wcet = byte_to_sched_time(stream.get_max_bytes_per_package(), current_switch.Mbits)
                        
                        
                        if stream.input_model.synchronous and self.synchronous:
                            if self.composed_objects:
                                current_task = composed_model.Task(stream.name + "_" + current_switch.name + "_Task_" + str(task_chain_id), wcet = _wcet, bcet = _bcet, scheduling_parameter = stream.priority,OutEventModelClass=composed_propagation.SyncComposedPropagationEventModel, priority =stream.priority)
                            else:
                                current_task = model.Task(stream.name + "_" + current_switch.name + "_Task_" + str(task_chain_id), wcet = _wcet, bcet = _bcet, scheduling_parameter = stream.priority,OutEventModelClass=propagation.SyncPropagationEventModel, priority =stream.priority)
                        else:
                            if self.composed_objects:
                            
                                current_task = composed_model.Task(stream.name + "_" + current_switch.name + "_Task_" + str(task_chain_id), wcet = _wcet, bcet = _bcet, scheduling_parameter = stream.priority, priority =stream.priority)
                            else:
                                current_task =          model.Task(stream.name + "_" + current_switch.name + "_Task_" + str(task_chain_id), wcet = _wcet, bcet = _bcet, scheduling_parameter = stream.priority, priority =stream.priority)
                        task_chain_id += 1
                        
                        stream.pycpa_ethernet_task_list.append(current_task)
                        current_switch.ports[k].pycpa_resource.bind_task(current_task)

            # Then add the Task for the last switch
            last_switch = stream.switch_list[len(stream.switch_list)-1]
            for k in range(0, len(last_switch.port_remote_names)):
                remote_entity = last_switch.port_remote_names[k]

                if str(remote_entity) == str(stream.end_NIC_endpoint):
                    # Then add the content
                    stream.pycpa_ethernet_hw_entity_list.append(last_switch)
                    stream.pycpa_ethernet_port_list.append(last_switch.ports[k])

                    _bcet = byte_to_sched_time(stream.get_max_bytes_per_package(), last_switch.Mbits)
                    _wcet = byte_to_sched_time(stream.get_max_bytes_per_package(), last_switch.Mbits)

                    if stream.input_model.synchronous:
                        if self.composed_objects:
                            current_task = composed_model.Task(stream.name + "_" + last_switch.name + "_Task_" + str(task_chain_id), wcet = _wcet, bcet = _bcet, scheduling_parameter = stream.priority,OutEventModelClass=composed_propagation.SyncComposedPropagationEventModel, priority =stream.priority)
                        else:
                            current_task = model.Task(stream.name + "_" + last_switch.name + "_Task_" + str(task_chain_id), wcet = _wcet, bcet = _bcet, scheduling_parameter = stream.priority,OutEventModelClass=propagation.SyncPropagationEventModel, priority =stream.priority)
                    else:
                        if self.composed_objects:
                            current_task = composed_model.Task(stream.name + "_" + last_switch.name + "_Task_" + str(task_chain_id), wcet = _wcet, bcet = _bcet, scheduling_parameter = stream.priority, priority =stream.priority)
                        else:
                            current_task = model.Task(stream.name + "_" + last_switch.name + "_Task_" + str(task_chain_id), wcet = _wcet, bcet = _bcet, scheduling_parameter = stream.priority, priority =stream.priority)
                        
                            
                    task_chain_id += 1
                    stream.pycpa_ethernet_task_list.append(current_task)
                    last_switch.ports[k].pycpa_resource.bind_task(current_task)

            # Introduce task precedence
            if self.composed_objects:
                path = model.Path("Path_" + stream.name,stream.pycpa_ethernet_task_list)
            else:
                path = model.Path("Path_" + stream.name,stream.pycpa_ethernet_task_list)
                
    
            stream.pycpa_path = path

            # Last introduce the input event model
            if isinstance(stream.input_model, cn.DDSStreamInputModel):
                if self.composed_objects:
                    data_rate = stream.pycpa_ethernet_task_list[0].resource.bits_per_second
                else:
                    data_rate = 0
                    
                
                    
                input_model = stream.create_sample_event_model(self.synchronous, self.composed_objects,speed(data_rate))
                
                
            elif isinstance(stream.input_model, cn.StreamInputModel):
                input_model = stream.create_pjd_event_model(self.synchronous)
            else:
                assert False
                
                
            # Store the input model
            stream.input_model.pycpa_event_model = input_model
            
            # Connect the input model
            stream.pycpa_ethernet_task_list[0].in_event_model = input_model

            if self.composed_objects:
                if isinstance(input_model, composed_model.SyncComposedEventModel):
                    for n in input_model.shaped_bursts:
                        shaped_bursts = input_model.shaped_bursts[n]
                        for k in shaped_bursts:
                            burst = shaped_bursts[k]
                            
                            burst.task = stream.pycpa_ethernet_task_list[0]

        return system
        



    def calculate_stream_latencies(self,task_results):
        
        for stream_key in self.cross_layer_model.ethernet_streams:
        
            stream = self.cross_layer_model.ethernet_streams[stream_key]
        
            if not self.synchronous or not stream.input_model.synchronous:
            
                if self.composed_objects:
                
                    first_task = stream.pycpa_ethernet_task_list[0]
                    latency = 0
                
                    for t in stream.pycpa_ethernet_task_list:
                        latency+=task_results[t].wcrt
                    
                    # Add sample perspective: Maximum distance between fragments
                    latency += latency + first_task.in_event_model.deltaplus_func(stream.input_model.number_of_fragments)
                    stream.sporadic_pycpa_ethernet_wcrt = latency
                    
                else:    
                    first_task = stream.pycpa_ethernet_task_list[0]
                    latency = 0
                
                    for t in stream.pycpa_ethernet_task_list:
                        latency+=task_results[t].wcrt
                    
                    # Add sample perspective: Maximum distance between fragments
                    latency += latency + first_task.in_event_model.deltaplus_func(stream.input_model.number_of_fragments)
                    stream.sporadic_pycpa_ethernet_wcrt = latency
            
            
            
            else:
            
               
                if self.composed_objects:
             
                    wcrt = 0
                    
                    
                    for n in range(0, int(self.cross_layer_model.hyperperiod/stream.input_model.sample_period_ns)):
                    
                        first_task = stream.pycpa_ethernet_task_list[0]
                        last_task  = stream.pycpa_ethernet_task_list[len(stream.pycpa_ethernet_task_list)-1]
                        
                        first_task_data_rate = stream.pycpa_ethernet_task_list[0].resource.bits_per_second
                        
                        current_burst_starting_time = task_results[first_task].busy_times[n][0].t_start + (1500*8*1000*1000*1000)/first_task_data_rate
                        current_burst_ending_time   = task_results[last_task].busy_times[n][len(task_results[last_task].busy_times[n])-1].t_end + task_results[last_task].busy_times[n][len(task_results[last_task].busy_times[n])-1].duration
                        
                        if (current_burst_ending_time - current_burst_starting_time)%self.cross_layer_model.hyperperiod > wcrt:
                            wcrt = (current_burst_ending_time - current_burst_starting_time)%self.cross_layer_model.hyperperiod
                            
                    stream.comp_pycpa_ethernet_wcrt =  wcrt
                    
                else: 
                

                    
                    wcrt = 0
          
                    for b_time in range(0, int(self.cross_layer_model.hyperperiod/stream.input_model.sample_period_ns)):
                
                        first_task = stream.pycpa_ethernet_task_list[0]
                        last_task  = stream.pycpa_ethernet_task_list[len(stream.pycpa_ethernet_task_list)-1]
                    
                        current_burst_start_fragment_index = b_time * stream.input_model.number_of_fragments
                        current_burst_end_fragment_index = current_burst_start_fragment_index + stream.input_model.number_of_fragments - 1
                    
                        first_time = first_task.in_event_model.deltamin_func(current_burst_start_fragment_index)
                        last_time = task_results[last_task].busy_times[current_burst_end_fragment_index]
                    
                        if last_time - first_time > wcrt:
                            wcrt = last_time - first_time
                            
                    stream.sync_pycpa_ethernet_wcrt = wcrt
                    #print("adas stream sync")

                    


    def collect_utilization_data(self, data, nbr_streams):

        # ["port", "nbr_streams", "speed", "byte_per_hyperperiod", "hyperperiod", "utilization"]

        current_line_nbr = len(data)
        
        for r in self.cross_layer_model.pycpa_sync_ethernet_model.resources:
        
            line = [None] * 6
            line[0] = r.name
            line[1] = nbr_streams
            line[2] = None
            line[3] = None
            line[4] = self.cross_layer_model.hyperperiod
            line[5] = r.load()
            
            data.loc[current_line_nbr] = line 
            current_line_nbr += 1
            
        return data
            



    def run_ethernet_analysis(self,data_frame):
        
        
        analysis_order = network_resource_dependence.create_network_resource_dependency_graph(self.cross_layer_model.pycpa_sync_ethernet_model)
        
        
        
        if self.composed_objects and self.synchronous:
            task_results = composed_analysis.analyze_system(self.cross_layer_model.pycpa_sync_ethernet_model,analysis_order = analysis_order)
        else:
            task_results = analysis.analyze_system(self.cross_layer_model.pycpa_sync_ethernet_model,analysis_order = analysis_order)
        
        
        self.cross_layer_model.pycpa_ethernet_results = task_results
        self.calculate_stream_latencies(task_results)


    def print_pycpa_ethernet_model(self, number):
        g = graph.graph_system(self.cross_layer_model.pycpa_sync_ethernet_model, './' + str(number) + '_pycpa_sync_ethernet_model.pdf')
        




































