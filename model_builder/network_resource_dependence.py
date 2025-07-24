"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Functions to efficiently organize analysis tasks to avoid duplicate analyses of tasks.
"""


# Import graph
import networkx as nx


def create_network_resource_dependency_graph(system):

    analysis_order = list()
    nodes = dict()
    Graph = nx.MultiDiGraph()
    
    # First create one node per resource
    for r in system.resources:
    
        nodes[r.name] = r
        
    for key in nodes:
        Graph.add_node(nodes[key], resource = r)
    
    task_count = 0
    for r in system.resources:
        
        for t in r.tasks:
            task_count = task_count + 1
            # check dependence of all tasks and add connection
            
            if t.scheduling_parameter == 0:
                continue
            
            for next_task in t.next_tasks:
            
                next_resource = next_task.resource
                
                if Graph.has_edge(r, next_resource):
                    continue
                    
                
                Graph.add_edge(r,next_resource)
                
                
                

    
    # Prio 1: Directly add if no predecessor
    for r in system.resources:
        
        # no dublicates
        if r in analysis_order:
                continue
                      
        predecessors = set()
            
        for pre in  Graph.predecessors(r):
            predecessors.add(pre)
            
        if len(predecessors) == 0:
            analysis_order.append(r)
            
    
    while len(analysis_order) < len(system.resources):
    

        no_successor_candidate = None

        nbr_dependencies_not_in_order = None
        fewest_dependencies_candidate = None
            
            
        for r in system.resources:
        
            # no dublicates
            if r in analysis_order:
                continue
                      
            predecessors = set()
            
            for pre in  Graph.predecessors(r):
                predecessors.add(pre)
            
            # Prio 2: Area of possible circular dependencies
            
            # Count number of successors
            successors = set()
            for suc in Graph.successors(r):
                successors.add(suc)
                
               
            if no_successor_candidate == None and len(successors) == 0:
                no_successor_candidate = r
                
            if len(successors) == 0:
                continue
            
            
                
            # Step 3: Find resource that has the lowest number of predecessors which are not in the current analysis order
            # Condition: Circular dependencies: 
            # Find one that has the fewest dependencies
            
            count = 0
            for pre in predecessors:
                if not pre in analysis_order:
                    count = count + 1
                    
            if fewest_dependencies_candidate == None:
                nbr_dependencies_not_in_order =  count
                fewest_dependencies_candidate = r
            else:
                if nbr_dependencies_not_in_order > count:
                    nbr_dependencies_not_in_order = count
                    fewest_dependencies_candidate = r 
            
        if not fewest_dependencies_candidate == None:
            analysis_order.append(fewest_dependencies_candidate)
        else:
            analysis_order.append(no_successor_candidate)
                  


    task_analysis_order = list()
    for r in analysis_order:
    
        for t in r.tasks:
        
            if t.scheduling_parameter == 0:
            
                task_analysis_order.append(t)
                
    nbr_adas_task_count = 0
    for r in analysis_order:
    
        for t in r.tasks:

            if t.scheduling_parameter == 1:
            
                task_analysis_order.append(t)
                nbr_adas_task_count += 1


    #nx.nx_agraph.to_agraph(Graph).write("./network_resource_dependence_" + str(nbr_adas_task_count) + ".dot")
    return task_analysis_order
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
