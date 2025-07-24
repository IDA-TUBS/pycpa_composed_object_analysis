"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

The composed object scheduler.

"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

import itertools
import math
import logging

from pycpa import analysis
from pycpa import options
from pycpa import model
from pycpa import propagation
from . import model as composed_model
from . import propagation as composed_propagation
from pycpa import schedulers

import numpy as np

logger = logging.getLogger("pycpa")


# priority orderings
prio_high_wins_equal_fifo = lambda a, b : a >= b
prio_low_wins_equal_fifo = lambda a, b : a <= b
prio_high_wins_equal_domination = lambda a, b : a > b
prio_low_wins_equal_domination = lambda a, b : a < b

# new imports...
try:
    from time import process_time as timefunc
except:
    from time import clock as timefunc
    

columns = ["timestamp", "workload", "locked_workload", "is_start_of_load", "is_end_of_load", "dict_burst_tw_to_wcrt"]
        
class SyncComposedObjectScheduler(schedulers.SPNPScheduler):
    """ Static-Priority-Preemptive Scheduler

    Priority is stored in task.scheduling_parameter,
    by default numerically lower numbers have a higher priority

    Policy for equal priority is FCFS (i.e. max. interference).
    """


    def __init__(self, hyperperiod, priority_cmp=prio_low_wins_equal_fifo):
    
        super().__init__()

        # # priority ordering
        self.priority_cmp = priority_cmp
        self.hyperperiod = hyperperiod


        self.max_sync_load_schedules = dict()

    def is_sync_task(self,task):
    
        return isinstance(task.in_event_model, composed_model.SyncComposedEventModel) or \
               isinstance(task.in_event_model, composed_propagation.SyncComposedPropagationEventModel)
               
               
               
    def stopping_condition(self, task, q, w):
        """ Check if we have looked far enough
            compute the time the resource is busy processing q activations of task
            and activations of all higher priority tasks during that time
            Returns True if stopping-condition is satisfied, False otherwise
        """

        # if there are no new activations when the current busy period has been completed, we terminate
        #if task.in_event_model.delta_min(q + 1) >= self.spnp_busy_period(task, w):
        #    return True
        return True
        
    def compute_bcrt(self, task, task_results=None):
        """ Return the best-case response time for q activations of a task.
        Convenience function which calls the minimum busy-time.
        The bcrt is also stored in task_results.

        """
        if not self.is_sync_task(task):
            return super().compute_bcrt(task, task_results)
            
        return
               
    def compute_wcrt(self, task, task_results=None):

        #print("compute_wcrt for task {} on resource {}".format(task.name,task.resource.name))
        
        # If not a synchronous task, then use classic sporadic wcrt analysis
        if not self.is_sync_task(task):
        
            #print("compute_wcrt for task {} on resource {}".format(task.name,task.resource.name))
            return super().compute_wcrt(task, task_results)


        # Compute synchronous shaped bursts
        logger.debug('compute shaped bursts of %s' % (task.name))
       
        task_results[task].busy_times = dict()
        
        wcrt = 0
        
        for n in range(0,task.in_event_model.get_activations_per_hyperperiod()):
        
            task_results[task].busy_times[n] = dict()
            
            # Input burst model
            burst_set_n = task.in_event_model.shaped_bursts[n]

            n_abs_end = 0

            for k in burst_set_n:
            
                shaped_burst_k = burst_set_n[k]
                
                # >>> Analyze the k-th burst of the n-th sample transmission <<<
                # Insert the shaped burst and receive the generated shaped bursts
                # k_abs_end is an integer (no modulo)
                # burst_set is a list()
                k_abs_end, burst_set = self.b_plus_sy(task, n, len(task_results[task].busy_times[n]), shaped_burst_k) 
                n_abs_end = k_abs_end # Take the last value
                
                # Add the bursts to the n-th burst set to propagate
                for new_k_burst in burst_set:                
                    task_results[task].busy_times[n][len(task_results[task].busy_times[n])] = new_k_burst
                    
            # Evaluate n-th WCRT
            _wcrt_candidate = n_abs_end - task.in_event_model.deltaplus_func(n)
                
            if _wcrt_candidate > wcrt or wcrt == 0:
                wcrt = _wcrt_candidate
                
                
        if task_results:
            task_results[task].q_wcrt = wcrt
            task_results[task].wcrt = wcrt
            task_results[task].b_wcrt = wcrt      
            
        return wcrt


    def compute_max_backlog(self, task, task_results, output_delay=0):
        """ Compute the maximum backlog of Task t.
        This is the maximum number of outstanding activations.
        Implemented as shown in Eq.17 of [Diemer2012]_.
        """
        return None

               
               
               
    def b_plus_sy(self, task, n, k,  shaped_burst_k):
        #print(" ========================== b_plus() ================================== ")
        #print("Compute burst propagation of " + str(task) + " with burst: ")
        #shaped_burst_k.represent()
        
        # Sanity check
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)

        # Create the maximum synchronous load schedule
        max_sync_load_schedule = self.calculate_max_sync_load_schedule(task, task.resource, task.scheduling_parameter)
        
        # k value incremented per overlapping interval
        current_k_in_n = k
        
        # Propagation of the k-th burst is subject to direct interference with other blocks' arrival functions relativ to the k-th blocks' process function
        current_burst_starting_time = shaped_burst_k.burst_load_late_arrival_time(0) # Initlially start at workload = 0B
        k_burst_ending_time  = shaped_burst_k.burst_load_late_arrival_time(shaped_burst_k.workload)
        
        # Initialize the burst iteration
        current_burst_ending_time = None
        new_shaped_bursts = []
        wcrt_of_input_burst_k = 0
        
        # Parameters for iteration
        cumulated_workload = 0
        end_condition = False
        
        flag_workload_is_zero = False
        
        while True:
        
            
            #print(" ------------------------------------------------------------------------------------------------- generated burst: ------------------------------------------------------------------------------------------------- ")
            #print("Burst duration starting time: " + str(current_burst_starting_time))
            #print("Burst duration ending time  : " + str(k_burst_ending_time))
            # 1st set propagated n and k' values of task i to i+1
            _n = n
            _k = current_k_in_n
            current_k_in_n += 1
            #print("_n: " + str(_n))
            #print("_k: " + str(_k))
            
            # 2nd: Calculate workload portions w_1 and w_2 based on other burst's arrival model
            current_burst_ending_time = self.get_next_start_of_load_arrival_after(max_sync_load_schedule, current_burst_starting_time, shaped_burst_k)
            if (current_burst_ending_time - current_burst_starting_time)%self.hyperperiod >=  (((shaped_burst_k.t_end + shaped_burst_k.duration)%self.hyperperiod) - current_burst_starting_time)%self.hyperperiod:
#                current_burst_ending_time = shaped_burst_k.burst_load_late_arrival_time(shaped_burst_k.workload)
                current_burst_ending_time = shaped_burst_k.t_end + shaped_burst_k.duration
                end_condition = True
                
                
            #print("Sub burst duration starting time: " + str(current_burst_starting_time))
            #print("Sub burst duration ending time  : " + str(current_burst_ending_time))

            time_difference = (current_burst_ending_time - current_burst_starting_time) % self.hyperperiod
            assert time_difference >= 1
            
            # 3rd: Calculate the t^- following w_1. Therefore keep the workload updated
            # Equation (17)
            min_frame_duration = int((1500*8*1000*1000*1000)/(shaped_burst_k.datarate))
            _t_start = (shaped_burst_k.t_start + int(cumulated_workload*(1000*1000*1000/shaped_burst_k.datarate)) + min_frame_duration) % self.hyperperiod
            
            # Increase the cumulated workload
            _workload = int(math.ceil((time_difference/shaped_burst_k.duration) * shaped_burst_k.workload))
            cumulated_workload = cumulated_workload + _workload
            #print("Cumulated workload: " + str(cumulated_workload) + "/" + str(shaped_burst_k.workload))
            
            # Sanity: Assert that workload is persistent
            assert cumulated_workload <= shaped_burst_k.workload + (1 + _k - k)

            # 4th Calculate the start of the propagated t^+
            schedule_row = self.get_schedule_row_at(max_sync_load_schedule, current_burst_starting_time)
            assert shaped_burst_k in schedule_row[columns.index('dict_burst_tw_to_wcrt')]
            # Equation (18) part 1
            _t_end = int(math.ceil(current_burst_starting_time + math.ceil(schedule_row[columns.index('dict_burst_tw_to_wcrt')][shaped_burst_k])))
     
            
            # 5th Calculate the end of the propagated w_2
            schedule_row = self.get_schedule_row_at(max_sync_load_schedule, current_burst_ending_time)
            assert shaped_burst_k in schedule_row[columns.index('dict_burst_tw_to_wcrt')]
            _end_of_propagated_processing = int(math.ceil(current_burst_ending_time + schedule_row[columns.index('dict_burst_tw_to_wcrt')][shaped_burst_k]))
            
            #print("_end_of_propagated_processing t^+: " + str(_end_of_propagated_processing))
            #print("WCRT: " + str(schedule_row[columns.index('dict_burst_tw_to_wcrt')][shaped_burst_k]))
            
            # 6th Calculate the duration
            _duration = (_end_of_propagated_processing - _t_end) % self.hyperperiod
            
            # Calculate the sporadic load: 
            CI_HP_all = self.spnp_high_priority_interference(task, _duration, task.scheduling_parameter)
            CI_HP_restr = self.spnp_high_priority_interference(task, (_t_end - _t_start)%self.hyperperiod, task.scheduling_parameter)
            CI_HP = CI_HP_all - CI_HP_restr
            
            if CI_HP >= _duration:
                print(CI_HP)
                print(CI_HP_restr)
                print(_duration)
            assert CI_HP < _duration
            _duration = _duration - CI_HP
            _t_end = _t_end + CI_HP
            
            #print(self.spnp_high_priority_interference(task, _duration, task.scheduling_parameter))
   
            
            # 8th Create the new burst to be propagated
            assert _duration > 0
            #print("duration: " + str(_duration))
            new_burst = composed_model.ShapedBurst(task, _n, _k, self.hyperperiod, (_t_start) %self.hyperperiod, (_t_end + min_frame_duration)%self.hyperperiod, _duration, _workload, task.resource.bits_per_second)
            #new_burst.represent()           
            
            # 9th: Add the burst to the propagation burst set
            new_shaped_bursts.append(new_burst)
            wcrt_of_input_burst_k = (_t_end - _t_start) % self.hyperperiod + _duration
            
          
            # Xth: Go to the next burst
            if end_condition == True or current_burst_starting_time == current_burst_ending_time:
                break
            
                
            current_burst_starting_time = current_burst_ending_time
           
        assert abs(cumulated_workload - shaped_burst_k.workload) + (1 + _k - k)
        
        # int , [list]
        # int: wcrt of the current burst
        # [list]: shaped bursts to add to the propagated output (event) model
        return wcrt_of_input_burst_k, new_shaped_bursts
        
        
        
        
        
        
    def low_priority_interference(self, task):
    
        b = 0
        for ti in task.get_resource_interferers():
            if self.priority_cmp(ti.scheduling_parameter, task.scheduling_parameter) == False:
                b = max(b, ti.wcet)
        return b


    def spnp_high_priority_interference(self, task, sync_load, scheduling_parameter, debug = False):
        """ Calculated the busy period of the current task
        """
        
        w = sync_load
        w_new = w
        while True:
            
            sporadic_interference_in_bw = 0
            
            for ti in task.get_resource_interferers():
            
                if self.priority_cmp(ti.scheduling_parameter, task.scheduling_parameter):
                                
                    if not self.is_sync_task(ti):
                    
                        sporadic_interference_in_bw += ti.wcet * ti.in_event_model.eta_plus(w_new + 1) # XXX scheduling granularity

            w_new = sync_load + sporadic_interference_in_bw
            
            assert w_new >= w
            
            if w_new == w:
                return sporadic_interference_in_bw
                
            w = w_new

        
    def get_schedule_row_at(self, max_sync_load_schedule, timestamp):
        
        # Check if value in schedule
        index_list = np.where(max_sync_load_schedule[:,0]==timestamp%self.hyperperiod)[0]
        if len(index_list) > 0:
            return max_sync_load_schedule[index_list[0]]
        assert False
            
           
        
    def get_schedule_value_at(self, max_sync_load_schedule, timestamp):
    
        # Check if value in schedule
        index_list = np.where(max_sync_load_schedule[:,0]==timestamp%self.hyperperiod)[0]
        if len(index_list) > 0:
            row = max_sync_load_schedule[index_list[0]]
            return row[columns.index('workload')]
        
        # Iterate through values
        current_index = 0
        current_row = max_sync_load_schedule[current_index]
        next_row = None
        
        
        
        while True:
        
            current_index = (current_index + 1) % len(max_sync_load_schedule)
            next_row = max_sync_load_schedule[current_index]
            
            ts_current_row = current_row[columns.index('timestamp')]
            ts_next_row    = next_row[columns.index('timestamp')]
                         
            
            if ((ts_current_row < timestamp) and (ts_next_row > timestamp)) or ((timestamp > ts_current_row) and (ts_current_row > ts_next_row)):
                
                time_difference_between_bounds = (ts_next_row - ts_current_row) % self.hyperperiod
                time_difference_to_timestamp   = (timestamp   - ts_current_row) % self.hyperperiod
                wl_current_row = current_row[columns.index('workload')]
                wl_next_row    = next_row[columns.index('workload')]
                wl_difference = wl_current_row - wl_next_row 
                return wl_current_row - time_difference_to_timestamp * (wl_difference/time_difference_to_timestamp)
            
            current_row = next_row
        
            while_counter += 1
            
            assert while_counter <= len(max_sync_load_schedule) + 2
        
    
    def composed_busy_window_analysis_at(self, resource, shaped_burst_k, max_sync_load_schedule, timestamp, reference_timestamp):
    
        time_difference = (reference_timestamp - timestamp) % self.hyperperiod
        
        # 1st Get value from schedule
        schedule_load_value = self.get_schedule_value_at(max_sync_load_schedule,timestamp)   
        
        # 2nd Substract all the non-relevant FIFO load in the schedule
        non_relevant_fifo_load_in_schedule = shaped_burst_k.arrival(reference_timestamp) - shaped_burst_k.process(reference_timestamp)
        
        # 3rd Add up all the newly arrived load from timestamp to reference_timestamp
        additional_synchronous_load_arrival = 0
        
        interfering_tasks = [ti for ti in resource.tasks if self.is_sync_task(ti)]
        
        for ti in interfering_tasks:
        
            for _n in range(0,ti.in_event_model.activations_per_hyperperiod):
            
                shaped_bursts_n = ti.in_event_model.shaped_bursts[_n]
            
                for _k in shaped_bursts_n:
                
                    shaped_burst = shaped_bursts_n[_k]
                    

                        
                    #if not (shaped_burst.n == shaped_burst_k.n and shaped_burst.k > shaped_burst_k.k): # XXX Alte Variante
                    
                    
                    
                    
                    if shaped_burst.n == shaped_burst_k.n and shaped_burst.k > shaped_burst_k.k and shaped_burst.task.name == shaped_burst_k.task.name:
                        continue
                    
                    additional_synchronous_load_arrival += shaped_burst.arrival(timestamp + time_difference) - shaped_burst.arrival(timestamp)
                    
        # Convert bits to time
        lp_and_sync_load = (schedule_load_value - non_relevant_fifo_load_in_schedule + additional_synchronous_load_arrival) *((1000*1000*1000)/resource.bits_per_second)
                    
        # 4th Add sporadic load
        sporadic_load_interference = self.spnp_high_priority_interference(interfering_tasks[0], lp_and_sync_load, shaped_burst_k.task.scheduling_parameter, debug=True)
        
        
        # 5th Lower priority blocking interference
        low_priority_blocking = self.low_priority_interference(interfering_tasks[0])
        
        # 6th Add interfering and sporadic load
        busy_window_time = lp_and_sync_load + sporadic_load_interference + low_priority_blocking
                
        return busy_window_time
        
        
    def get_next_start_of_load_arrival_after(self, sy_schedule, timestamp, burst):
        
        # Default value after complete iteration through the schedule
        wc_value = burst.t_end + burst.duration
        
        # XXX Including the own shaped burst!
       
        	
        # Get sy_schedule row of timestamp
        index_list =   np.where(sy_schedule[:,0]==(timestamp%self.hyperperiod))[0]

        # Assert that the timestamp has an existing value
        assert len(index_list) > 0
        index_column = index_list[0]
        row = sy_schedule[index_column]

        start_index = index_column
        while True:
        
            index_column = (index_column + 1) % len(sy_schedule)
            
            if index_column == start_index:
                return wc_value #Return upper default value
            
            comp_row = sy_schedule[index_column]

            
            
            for _burst in comp_row[columns.index('is_start_of_load')]:
                
                if burst.task == _burst.task: # and burst.n == burst.n and burst.k >= _burst.k:
                    continue
                    
                return comp_row[columns.index('timestamp')]


            for _burst in comp_row[columns.index('is_end_of_load')]:
                
                if burst.task == _burst.task: # and burst.n == burst.n and burst.k > _burst.k:
                    continue
                    
                return comp_row[columns.index('timestamp')]      


    def print_max_sync_load_schedule(self, schedule, resource):
    
        # columns = ["timestamp", "workload", "locked_workload", "is_start_of_load", "is_end_of_load", "dict_burst_tw_to_wcrt"]
    
        print("===============================================================================================================")
        value = 100
        
        print("--------------------- print maximum sync load schedule for resource: " + str(resource) + " below the value " + str(value) + "ms ---------------------")
 
        
        for i in range(0, len(schedule)):
       
            current_row = schedule[i]
            
            #if current_row[columns.index('timestamp')]/1000000 >= value:
            #    break
       
            print(str(i) + ": " +  '{:6s}'.format(str(current_row[columns.index('timestamp')]/1000000)) + "  " +  '{:8s}'.format(str(current_row[columns.index('workload')])) + "  \t" + '{:8s}'.format(str(current_row[columns.index('locked_workload')])) + "  \t" + str(current_row[columns.index('is_start_of_load')])  + "  \t" + str(current_row[columns.index('is_end_of_load')]) + " " +   str((current_row[columns.index('dict_burst_tw_to_wcrt')])))
        

        #print(" ---- Source Tasks and bursts ---- ")
        
        if resource == None:
            print("===============================================================================================================")
            return
            
        
        interfering_tasks = [ti for ti in resource.tasks if self.is_sync_task(ti)]
        
        for ti in interfering_tasks:
        
            #print("Task: " + str(ti.name))
        
            for n in range(0,ti.in_event_model.activations_per_hyperperiod):
            
                shaped_bursts_n = ti.in_event_model.shaped_bursts[n]
            
                for k in shaped_bursts_n:
                
                    shaped_burst = shaped_bursts_n[k]

                    #shaped_burst.represent()
                    #print()
        #print("===============================================================================================================")
        
        
        
    def calculate_max_sync_load_schedule(self,task, resource, scheduling_parameter):

        # Check if a maximum synchronous load schedule for that resource already exists and return in that case
        if scheduling_parameter in self.max_sync_load_schedules:
            if not self.max_sync_load_schedules[scheduling_parameter] is None:
                return self.max_sync_load_schedules[scheduling_parameter]

        #print("calculate_max_sync_load_schedule() for resource " + str(resource) + " with priority " + str(scheduling_parameter))
        # Create an empty maximum synchronous load schedule
        
        # columns = ["timestamp", "workload", "locked_workload", "is_start_of_load", "is_end_of_load", "dict_burst_tw_to_wcrt"]

        ############################################################################################################
        ############################## First step: Initialization of schedule entires ##############################
        ############################################################################################################
        
        # Initialize the schedule
        sy_schedule = np.empty((0,len(columns)),int)
        
        # All synchronous tasks on the resource
        interfering_tasks = [ti for ti in resource.tasks if self.is_sync_task(ti)]
        
        for ti in interfering_tasks:
        
            # Sanity: Assert that synchronous tasks have the same priority (model assumption)
            assert ti.scheduling_parameter == task.scheduling_parameter
        
            for n in range(0,ti.in_event_model.activations_per_hyperperiod):
            
                shaped_bursts_n = ti.in_event_model.shaped_bursts[n]
            
                for k in shaped_bursts_n:
                
                    # Fill the schedule with initial values in correspondence to shaped bursts
                    shaped_burst = shaped_bursts_n[k]
            
                    t_start  = shaped_burst.t_start
                    if not t_start in sy_schedule[:, columns.index('timestamp')]:
                        new_row = [None] * len(columns)
                        new_row[columns.index('timestamp')] = t_start % self.hyperperiod
                        new_row[columns.index('workload')] = 0
                        new_row[columns.index('locked_workload')] = 0
                        new_row[columns.index('is_start_of_load')] = set() 
                        new_row[columns.index('is_start_of_load')].add(shaped_burst)
                        new_row[columns.index('is_end_of_load')] =   set() 
                        sy_schedule = np.append(sy_schedule,np.array([new_row]), axis = 0)
                    else:
                        index_first_column = np.where(sy_schedule[:,0]==t_start)[0][0]
                        index_row = sy_schedule[index_first_column]
                        index_row[columns.index('is_start_of_load')].add(shaped_burst)
                        
                        
        
                    t_end = shaped_burst.t_end
                    if not t_end in sy_schedule[:,columns.index('timestamp')]:
                        new_row = [None] * len(columns)
                        new_row[columns.index('timestamp')] = t_end % self.hyperperiod
                        new_row[columns.index('workload')] = 0
                        new_row[columns.index('locked_workload')] = 0
                        new_row[columns.index('is_start_of_load')] = set()
                        new_row[columns.index('is_end_of_load')] = set()
                        sy_schedule = np.append(sy_schedule,np.array([new_row]), axis = 0)
                        
                        
                    t_start_plus_duration = ((shaped_burst.t_start + math.ceil((shaped_burst.workload*1000*1000*1000)/shaped_burst.datarate)) % self.hyperperiod) # FOLLOWING EARLY ARRIVAL! Rename to t_start_plus_early_arrival XXX
                    if not t_start_plus_duration in sy_schedule[:,columns.index('timestamp')]:
                        new_row = [None] * len(columns)
                        new_row[columns.index('timestamp')] = t_start_plus_duration
                        new_row[columns.index('workload')] = 0
                        new_row[columns.index('locked_workload')] = 0
                        new_row[columns.index('is_start_of_load')] = set()
                        new_row[columns.index('is_end_of_load')] = set()
                        new_row[columns.index('is_end_of_load')].add(shaped_burst)
                        sy_schedule = np.append(sy_schedule,np.array([new_row]), axis = 0)
                    else:
                        index_first_column = np.where(sy_schedule[:,0]==t_start_plus_duration)[0][0]
                        index_row = sy_schedule[index_first_column]
                        index_row[columns.index('is_end_of_load')].add(shaped_burst)
                        
                        
                    t_end_plus_duration = (shaped_burst.t_end  + shaped_burst.duration) % self.hyperperiod
                    if not t_end_plus_duration in sy_schedule[:,columns.index('timestamp')]:
                        new_row = [None] * len(columns)
                        new_row[columns.index('timestamp')] = t_end_plus_duration
                        new_row[columns.index('workload')] = 0
                        new_row[columns.index('locked_workload')] = 0
                        new_row[columns.index('is_start_of_load')] = set()
                        new_row[columns.index('is_end_of_load')] = set()
                        sy_schedule = np.append(sy_schedule,np.array([new_row]), axis = 0)
                    
        # Add the zero value at t = 0
        if not 0 in sy_schedule[:,columns.index('timestamp')]:
            zero_row = [None] * len(columns)
            zero_row[columns.index('timestamp')] = 0
            zero_row[columns.index('workload')] = 0
            zero_row[columns.index('locked_workload')] = 0
            zero_row[columns.index('is_start_of_load')] = set()
            zero_row[columns.index('is_end_of_load')] = set()
            sy_schedule = np.append(sy_schedule,np.array([zero_row]), axis = 0)
                    
        # Sort the array
        sy_schedule = sy_schedule[sy_schedule[:, columns.index('timestamp')].argsort()]
        
        
        ########################################################################################################
        ############################## Second step: Calculate the schedule values ##############################
        ########################################################################################################
        
        # Initialization
        current_schedule_index = 0
        previous_row = sy_schedule[current_schedule_index]
        current_row = None
        hyperperiod_iteration  = 1
        last_workload_value = 0
        
        
        while True:
        
            # --------------------- Step through the schedule ------------------
            current_schedule_index = (current_schedule_index + 1) % len(sy_schedule)
            
            if current_schedule_index == 0:
                hyperperiod_iteration += 1
            current_row = sy_schedule[current_schedule_index]
            # Workload to be checked in the end
            pre_evaluation_workload = current_row[columns.index('workload')]
            
            # --------------------- Calculate the next workload values ---------------------
            
            # Iterate through all shaped bursts on that resource
            t_start = previous_row[columns.index('timestamp')]
            t_end   = current_row[columns.index('timestamp')]
            time_difference = (t_end - t_start)%self.hyperperiod
            
            total_new_arrival = 0
            total_new_locked = 0
            
            for ti in interfering_tasks:
            
                for n in range(0,ti.in_event_model.activations_per_hyperperiod):
            
                    shaped_bursts_n = ti.in_event_model.shaped_bursts[n]
                    
                    for k in shaped_bursts_n:
                
                        shaped_burst = shaped_bursts_n[k]
                                                     
                        # Equation (7)
                        new_locked_value = shaped_burst.arrival(t_end) - shaped_burst.process(t_end)
                        assert new_locked_value >= 0
                        total_new_locked = total_new_locked + new_locked_value
                        
                        # Preevaluation for Equation (8)
                        new_arrival_value = shaped_burst.arrival(t_start + time_difference) - shaped_burst.arrival(t_start)
                        assert new_arrival_value >= 0
                        total_new_arrival = total_new_arrival + new_arrival_value

            
            # Write back data (result of Equation 7)
            current_row[columns.index('locked_workload')] = total_new_locked
                            
            # --> Equation (8): Calculate the schedule values
            # 1. Add the newly arrived workload
            current_row[columns.index('workload')] = previous_row[columns.index('workload')] + total_new_arrival
            
            # 2. Check the difference to the locked load
            free_to_process = current_row[columns.index('workload')] - total_new_locked
            
            # 3. Substract the maximum processable workload, but always stay above 0
            maximum_possible_processing_by_data_rate = time_difference * (resource.bits_per_second/(1000*1000*1000))
            current_row[columns.index('workload')] = max(0,current_row[columns.index('workload')]  - min(maximum_possible_processing_by_data_rate, free_to_process))

            # Breaking condition
            if hyperperiod_iteration > 1 and pre_evaluation_workload == current_row[columns.index('workload')]:
                break
                
            # Sanity check: 3rd iteration cannot be reached when bein schedulable
            assert hyperperiod_iteration < 3 
            #print("Nexyt iteration")
        
            # Step through the schedule ...
            previous_row = current_row

        ####################################################################################################
        ################################# Third step: Do the WCRT analysis #################################
        ####################################################################################################
        
        # ---> INFO <---
        #columns = columns = ["timestamp", "workload", "locked_workload", "is_start_of_load", "is_end_of_load", "dict_burst_tw_to_wcrt"]
        # timestamp := timestamp in schedule
        # workload  := L^+
        # locked_workload := L^-
        # is_start_of_load := 
        # is_end_of_load   := 
        # dict_burst_tw_to_wcrt := 
        
        count_dict_entries = 0
        #  Add all t_w1 and t_w2 with corresponding burst to the schedule.
        for i in range(0, len(sy_schedule)):
       
       
            current_row = sy_schedule[i]
            
            current_row_timestamp = current_row[columns.index('timestamp')]
            
            current_row[columns.index('dict_burst_tw_to_wcrt')] = dict()
            
            for ti in interfering_tasks:
        
                for n in range(0,ti.in_event_model.activations_per_hyperperiod):
            
                    shaped_bursts_n = ti.in_event_model.shaped_bursts[n]
            
                    for k in shaped_bursts_n:
                
                        shaped_burst = shaped_bursts_n[k]
            
            
                        
                        # Only put needed values into the dict at the corresponding time values
                        if shaped_burst.t_end + shaped_burst.duration < self.hyperperiod:
                            if current_row_timestamp >=  shaped_burst.t_end and current_row_timestamp <= shaped_burst.t_end + shaped_burst.duration:
                                current_row[columns.index('dict_burst_tw_to_wcrt')][shaped_burst] = -1
                                count_dict_entries += 1
                        else:
                            if current_row_timestamp <= (shaped_burst.t_end + shaped_burst.duration) % self.hyperperiod or current_row_timestamp >= shaped_burst.t_end:
                                current_row[columns.index('dict_burst_tw_to_wcrt')][shaped_burst] = -1
                                count_dict_entries += 1
                             
        
                        #current_row[columns.index('dict_burst_tw_to_wcrt')][shaped_burst] = -1
        # Complexity measure               
        #print("dict entries: " + str(count_dict_entries))
                        
            
        bw_calculations = 0
        
        for i in range(0, len(sy_schedule)):
            
            #print("i:" + str(i) + "/" + str(len(sy_schedule)))
            current_row = sy_schedule[i]
        
            current_row_timestamp = current_row[columns.index('timestamp')]
        
            for offset in range(0,len(sy_schedule)):
            
                comp_row = sy_schedule[(i+offset)%len(sy_schedule)]
                
                comp_row_timestamp = comp_row[columns.index('timestamp')]
                
                time_difference = (comp_row_timestamp - current_row_timestamp)%self.hyperperiod
            
                break_condition = False
                    
                for burst in comp_row[columns.index('dict_burst_tw_to_wcrt')]:
                    
                    bw = self.composed_busy_window_analysis_at(resource, burst, sy_schedule, current_row_timestamp, comp_row_timestamp) 
                    bw_calculations += 1
                    wcrt = bw - time_difference
                                        
                    
                    if wcrt > comp_row[columns.index('dict_burst_tw_to_wcrt')][burst]:
                    
                        comp_row[columns.index('dict_burst_tw_to_wcrt')][burst] = wcrt
            
                if break_condition:
                    break
                    
        
        ######################################################################################################
        ################################# Fourth step: Assert the evaluation #################################
        ######################################################################################################
        for i in range(0, len(sy_schedule)):
       
            current_row = sy_schedule[i]
            
            for burst in current_row[columns.index('dict_burst_tw_to_wcrt')]:
            
                assert current_row[columns.index('dict_burst_tw_to_wcrt')][burst] > -1
        
        # Debug print out
        #self.print_max_sync_load_schedule(sy_schedule, resource)
        self.max_sync_load_schedules[scheduling_parameter] = sy_schedule
        
        #print("return schedule")
        return sy_schedule
        
        
        
        
        
        
