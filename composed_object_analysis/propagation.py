"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Added synchronous and composed propagation models.

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division


from pycpa import options
from pycpa import model as pycpa_model
from pycpa import propagation as pycpa_propagation
from . import model

def default_propagation_method():
    method = options.get_opt('propagation')

    if method == 'jitter_offset':
        return pycpa_propagation.JitterOffsetPropagationEventModel
    elif method == 'busy_window':
        return pycpa_propagation.BusyWindowPropagationEventModel
    elif  method == 'jitter_dmin' or method == 'jitter':
        return pycpa_propagation.JitterPropagationEventModel
    elif method == 'jitter_bmin':
        return pycpa_propagation.JitterBminPropagationEventModel
    elif method == 'optimal':
        return pycpa_propagation.OptimalPropagationEventModel
    else:
        raise NotImplementedError

class SyncComposedPropagationEventModel(pycpa_model.EventModel):

    def __init__(self, task, task_results, nonrecursive=True):

        # Instrument super constructor
        name = task.in_event_model.__description__ + "_++"
        pycpa_model.EventModel.__init__(self,name,task.in_event_model.container)
        
        assert isinstance(task.in_event_model,model.SyncComposedEventModel) or isinstance(task.in_event_model,SyncComposedPropagationEventModel)

        self.hyperperiod = task.in_event_model.hyperperiod
        self.P = task.in_event_model.P
        self.activations_per_hyperperiod = int(self.hyperperiod/self.P)
        self.workload = task.in_event_model.workload
        self.datarate = task.in_event_model.datarate 
        
        self.task = task
        
        # Propagate shaped bursts
        self.shaped_bursts = task_results[task].busy_times

        self.__description__ = "Prop: HP={} P={}".format(self.hyperperiod,self.P)

    def get_activations_per_hyperperiod(self):
        return self.activations_per_hyperperiod

    def deltamin_func(self,n):
        
        _n = self.activations_per_hyperperiod
        
        shaped_burst = self.shaped_bursts[n][0]
        
        return shaped_burst.t_start
        
    def deltaplus_func(self,n):
        _n = self.activations_per_hyperperiod
        
        shaped_burst = self.shaped_bursts[n][0]
        
        return shaped_burst.t_start + shaped_burst.duration



    def load(self, accuracy=1000):
        """ Returns the asymptotic load,
        i.e. the avg. number of events per time
        """
         
        return ((self.activations_per_hyperperiod * (self.workload*8/self.datarate))/self.hyperperiod)  * 1000*1000*1000











