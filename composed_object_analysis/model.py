"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Changed 
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

import math
import logging
import copy
import warnings

from pycpa import options
from pycpa import util
from pycpa import model as pycpa_model

INFINITY = float('inf')

logger = logging.getLogger(__name__)


class ShapedBurst(pycpa_model.EventModel):
   
    def __init__(self, _task, _n, _k, _hyperperiod, _t_start, _t_end, _duration, _workload, _datarate):
   

        self.task = _task
        self.n = _n
        self.k = _k
        self.t_start = _t_start
        self.t_end = _t_end
        self.duration = _duration
        self.workload = _workload
        self.datarate = _datarate
        self.hyperperiod = _hyperperiod
       
        # Sanity Check
        assert (_t_end - _t_start) % _hyperperiod + _duration < _hyperperiod
        
       
       
    def __repr__(self):
        return "n={} k={} start={} end={} duration={} workload={} task={}".format(self.n,self.k,self.t_start,self.t_end,self.duration,self.workload,self.task)
       
       
    def arrival(self, t):
        return max(0,min(self.workload,(((t-self.t_start)%self.hyperperiod)*self.datarate)/1000000000)) + math.floor((t-self.t_start)/self.hyperperiod)*self.workload
       
    def process(self, t):
        _t_end = self.t_start + (self.t_end - self.t_start) % self.hyperperiod
        
        return max(0,min(self.workload,((t-_t_end)%self.hyperperiod)*(self.workload/self.duration)))    + math.floor((t-_t_end)/self.hyperperiod)*self.workload
       
    def locked(self, t):
        return self.arrival(t) - self.process(t)

    def represent(self):
   
        print("---- Shaped Burst ----")
        print("task    : " + str(self.task))
        print("n       : " + str(self.n))
        print("k       : " + str(self.k))
        print("t_start : " + str(self.t_start))
        print("t_end   : " + str(self.t_end))
        print("duration: " + str(self.duration))
        print("workload: " + str(self.workload))
        print("datarate: " + str(self.datarate))
        print("----------------------")

    def represent_arrival_and_process(self, ts):
        print("ts: " + str(ts) + "; arrival: " + str(self.arrival(ts)) + "; process: " + str(self.process(ts))) 


   
    def burst_load_late_arrival_time(self, _workload):
        """ Equation 10
        """
        
        assert _workload >= 0 and _workload <= self.workload
        
        return self.t_end + (float(_workload)/float(self.workload)) * self.duration


    def represent_arrival_and_process_over_time(self):
    
        self.represent_arrival_and_process(self.t_start)
        self.represent_arrival_and_process(self.t_end)
        self.represent_arrival_and_process(self.t_start + (self.workload*1000*1000*1000)/self.datarate)
        self.represent_arrival_and_process(self.t_end + 1000*1000)
        self.represent_arrival_and_process(self.t_end + self.duration)



class SyncComposedEventModel(pycpa_model.EventModel):
    """ The event model for the logical execution time programming model.
        It is based on a Period, Jitter and offset parametrization.
    """

    def __init__(self, hyperperiod, P, J, phi, _workload, _datarate, name='sync_emm', **kwargs):
        """ Period and offset place the activation into the hyperperiod.
            The Jitter, adds uncertaintiy.
        """
        pycpa_model.EventModel.__init__(self, name, **kwargs)

        self.set_model(hyperperiod, P,J,phi, _workload, _datarate)

    def set_model(self, hyperperiod, P, J, phi, _workload, _datarate):

        pycpa_model._warn_float(P, "Period")
        pycpa_model._warn_float(J, "Jitter")
        pycpa_model._warn_float(phi, "Offset")

        self.P=P
        self.J=J
        self.phi= phi  % self.P
        self.hyperperiod = hyperperiod
        self.workload = _workload
        self.datarate = _datarate
        
        self.activations_per_hyperperiod = int(self.hyperperiod/self.P)

        self.shaped_bursts = dict()

        for n in range(0,self.activations_per_hyperperiod):
            self.shaped_bursts[n] = dict()
            
            min_frame_size = 1500
            min_frame_duration = 0 
            min_frame_duration = (1500*8*1000*1000*1000)/self.datarate
            self.shaped_bursts[n][0] = ShapedBurst(None, n,0,self.hyperperiod, (self.deltamin_func(n)-min_frame_duration)%hyperperiod,self.deltaplus_func(n), ((self.workload*8*1000*1000*1000)/self.datarate),  self.workload*8, self.datarate)


        assert self.hyperperiod%self.P == 0, "Invalid Period of synchronous task. Not harmonized with the hyperperiod"
        assert self.J%2 == 0, "Jitter is: " + str(self.J)
        self.__description__ = "HP={} P={} J={} phi={}".format(hyperperiod,P,J,phi)

    def get_shaped_burst_n(self, n):
        return self.shaped_bursts[n]


    def load(self, accuracy=1000):
        """ Returns the asymptotic load,
        i.e. the avg. number of events per time
        """
        return ((self.activations_per_hyperperiod * (self.workload*8/self.datarate))/self.hyperperiod)  * 1000*1000*1000
        
        #return (float(accuracy)*(self.workload/(8*1500))) / float((float(accuracy)/self.activations_per_hyperperiod)*float(self.hyperperiod))

    def get_activations_per_hyperperiod(self):
        return self.activations_per_hyperperiod

    def deltamin_func(self,n):
        return self.P * n + self.phi

    def deltaplus_func(self,n):
        return self.P * n + self.phi + self.J

    def eta_min_sy(self,t):        
        return len([n for n in range(0,self.activations_per_hyperperiod) if (self.deltamin_func(n) % self.hyperperiod) <= (t%self.hyperperiod)]) \
               + self.activations_per_hyperperiod*int(t/self.hyperperiod)
    def eta_plus_sy(self,t):
        return len([n for n in range(0,self.activations_per_hyperperiod) if (self.deltaplus_func(n) % self.hyperperiod) <= (t%self.hyperperiod)]) \
               + self.activations_per_hyperperiod*int(t/self.hyperperiod)
               
               


               



class SampleEventModel(pycpa_model.EventModel):

    def __init__(self, sample_period, burst_size_nbr , d_min, jitter = 0, **kwargs):

        self.name = "SampleEventModel"

        pycpa_model.EventModel.__init__(self, self.name, kwargs)

        self.sample_period = sample_period
        self.burst_size_nbr = burst_size_nbr 
        self.dmin = d_min
        self.J = jitter 

    def deltaplus_func(self, n):
        if n < 2:
            return 0
        return self.sample_period*math.floor((n-1)/self.burst_size_nbr)+((n-1)%self.burst_size_nbr)*self.dmin + self.J

    def deltamin_func(self,n):
        if n < 2:
            return 0

        if self.burst_size_nbr == 0 or self.sample_period >= INFINITY:
            return 0
        if n == INFINITY:
            return INFINITY

        return max((n-1) * self.dmin, self.sample_period*math.floor((n-1)/self.burst_size_nbr)+((n-1)%self.burst_size_nbr)*self.dmin - self.J)


    def load(self, accuracy=1000):
        """ Returns the asymptotic load,
        i.e. the avg. number of events per time
        """    
        return float(accuracy) / ( float( (float(accuracy)/(self.burst_size_nbr)) * self.sample_period))
  
        
class Resource (pycpa_model.Resource):
    """ A Resource provides service to tasks. """

    def __init__(self, name=None, scheduler=None, bits_per_second=None, **kwargs):
        """ CTOR """

        super.__init__(name, scheduler)
        
        # # Ethernet port speed
        self.bits_per_second = bits_per_second




class Task(pycpa_model.Task):
    """ A Task is an entity which is mapped on a resource and consumes service.
    Tasks are activated by events, which are described by EventModel.
    Events are queued in FIFO order at the input of the task,
    see Section 3.6.1 in [Jersak2005]_ or Section 3.1 in [Henia2005]_.
    """

    def __init__(self, name, *args, **kwargs):
        """ CTOR """
        
        super.__init__(name)
        
    def load(self, accuracy=100):
        """ Returns the load generated by this task """
        
        if isinstance(self.in_event_model, SyncComposedEventModel) or "SyncComposedPropagationEventModel" in str(self.in_event_model.__class__):
            return self.in_event_model.load(accuracy)
        
        return self.in_event_model.load(accuracy) * float(self.wcet)



















