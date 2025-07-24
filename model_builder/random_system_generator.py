"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Functions for random stream deployment.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from model_builder.cross_layer_model import clm
from model_builder.cross_layer_model import clm_nodes as cn
from model_builder.cross_layer_model import clm_edges as ce
import copy

''' Author: Jonas '''


from random import seed      as seed
from random import random    as rnd
from random import randrange as rnd_range


class PseudoRandomGenerator:

    def __init__(self, seed=0):
        
        # Initialize the seed
        self.seed = seed
        self.set_seed(seed)

    def set_seed(self, _seed):
        self.seed = _seed
        seed(self.seed)

    def random_value_0_1(self):
        return rnd()

    def random_value_in_int_interval(self,start,end):
        
        _start = int(start)
        _end = int(end) + 1

        assert _end >= _start, "Error: start > end in random number generation"

        return rnd_range(_start, _end)
        
        
        
def generate_random_shortest_stream(r_generator, system, start_nic, end_nic):

    

   # --- No search the path ---
    current_paths = list()
    visited_nodes = list()
    valid_paths = list()

    # --- Get the first switch ---
    current_paths.append([system.switches[start_nic.port_remote_name]])
    visited_nodes.append(system.switches[start_nic.port_remote_name])

   # --- get paths ---
    while 1:
        new_paths = list()
        new_visited = list()

        for path in current_paths:


            # Get last path element
            last_path_element = path[len(path)-1]
            
            if not isinstance(last_path_element,cn.Switch):
                continue

            # Search switches
            for next_hop in last_path_element.port_remote_names:

                if next_hop == None:
                    continue
      
                # Check for end_nic
                if next_hop in system.NIC_endpoints:
                    endpoint = system.NIC_endpoints[next_hop]

                    if endpoint == end_nic:
                        _copy = copy.copy(path)
                        _copy.append(endpoint)
                        valid_paths.append(_copy)

                    # Always end at an endpoint
                    continue

                # Check if Switch
                if next_hop in system.switches:
                    switch = system.switches[next_hop]

                    if switch in visited_nodes:
                        continue

                    if not switch in visited_nodes:

                        new_visited.append(switch)
                        _copy = copy.copy(path)
                        _copy.append(switch)
                                                
                        new_paths.append(_copy)


        # Check break condition
        if len(new_paths) == 0:
            break

        # Refresh paths
        current_paths = new_paths

        # Pass newly visited nodes
        for node in new_visited:
            if not node in visited_nodes:
                visited_nodes.append(node)
        new_visited = list()


    assert len(valid_paths) > 0 , "No valid path when randomly generating a stream"

    # Now get the shortest paths:
    min_size = None
    for path in valid_paths:
        if min_size == None:
            min_size = len(path)
            continue

        if min_size > len(path):
           min_size = len(path)

    # Get all paths with min size
    relevant_paths = list()
    for path in valid_paths:
        if len(path) == min_size:
            relevant_paths.append(path)

    # Now get the path randomly and return it
    random_path = relevant_paths[r_generator.random_value_in_int_interval(0,len(relevant_paths)-1)]    
    return [start_nic] + random_path



def add_n_streams_to_clm(r_generator,system,n,NIC_endpoints):

    # First get two random NICs
    assert len(NIC_endpoints) > 1 , "Too few NIC_endpoints for random stream generation! (<=1)"

    for i in range(0,n):

        start_nic_id = r_generator.random_value_in_int_interval(0,len(NIC_endpoints)-1)
        end_nic_id = r_generator.random_value_in_int_interval(0,len(NIC_endpoints)-1)
    
        while end_nic_id == start_nic_id:
            end_nic_id = r_generator.random_value_in_int_interval(0,len(NIC_endpoints)-1)

        start_nic = list(NIC_endpoints.values())[start_nic_id]
        end_nic   = list(NIC_endpoints.values())[end_nic_id]

        random_stream = generate_random_shortest_stream(r_generator, system, start_nic, end_nic)

        # Now add the stream to the CLM
        system.add_ethernet_stream("Random_Stream_" + str(system.random_stream_count), random_stream[0], random_stream[1:len(random_stream)-1],random_stream[len(random_stream)-1], 2)
        system.random_stream_count = system.random_stream_count + 1















