"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Adapted two methods of the analysis.py
from pycpa.
"""


import gc
import logging
import copy
import time
#from collections import deque
import functools

try:
    from time import process_time as timefunc
except:
    from time import clock as timefunc

from . import model as composed_model
from . import propagation as composed_propagation
from pycpa import model
from pycpa import options
from pycpa import util
from pycpa import analysis as pycpa_analysis

gc.enable()
logger = logging.getLogger(__name__)





def analyze_task(task, task_results):
    """ Analyze Task BUT DONT propagate event model.
    This is the "local analysis step", see Section 7.1.4 in [Richter2005]_.
    """
    assert task is not None
    assert task_results is not None
    assert task in task_results

    for t in task.resource.tasks:
        assert (t.in_event_model is not None), 'task must have event model'

    assert (task.bcet <= task.wcet), 'BCET must not be larger '\
            'than WCET for task %s' % (task.name)

    task.update_execution_time(task_results)

    task.resource.scheduler.compute_bcrt(task, task_results)
    task.resource.scheduler.compute_wcrt(task, task_results)
    task.resource.scheduler.compute_max_backlog(task, task_results)

    if not task.resource.scheduler.is_sync_task(task):
        assert (task_results[task].bcrt <= task_results[task].wcrt),\
                'Task:%s, BCRT (%d) must not be larger than WCRT (%d)' % \
                (task.name, task_results[task].bcrt, task_results[task].wcrt)



               

def analyze_system(system, task_results=None, only_dependent_tasks=False,
                   progress_hook=None, analysis_order = None, **kwargs):
    """ Analyze all tasks until we find a fixed point

        system -- the system to analyze
        task_results -- if not None, all intermediate analysis
        results from a previous run are reused

        Returns a dictionary with results for each task.

        This based on the procedure described in Section 7.2 in [Richter2005]_.
    """
    
    if task_results is None:
        task_results = dict()
        for r in system.resources:
            for t in r.tasks:
                if not t.skip_analysis:
                    task_results[t] = pycpa_analysis.TaskResult()
                    t.analysis_results = task_results[t]

    analysis_state = pycpa_analysis.GlobalAnalysisState(system, task_results)



    analysis_state.analysisOrder = analysis_order
    
    iteration = 0
    start = timefunc()
    logger.debug("analysisOrder: %s" % (analysis_state.analysisOrder))
    
    last_resource = None
     
    count = 0 
    while len(analysis_state.dirtyTasks) > 0:

        if progress_hook is not None:
            progress_hook(analysis_state)

        logger.info("Analyzing, %d tasks left" %
                   (len(analysis_state.dirtyTasks)))

        # explicitly invoke garbage collection because there seem to be circluar references
        # TODO should be using weak references instead for model propagation
        gc_count = gc.collect()
        
        # Always prefer high priority sporadic control tasks
        control_is_dirty = False
        for check_task in analysis_state.analysisOrder:
            if "ControlStream" in check_task.name:
                if check_task in analysis_state.dirtyTasks:
                    control_is_dirty = True
                    
                  
        for t in analysis_state.analysisOrder:
            
            if t not in analysis_state.dirtyTasks:
                continue
                
            if "ADASStream" in t.name and control_is_dirty == True:
                continue


            if hasattr(r.scheduler, 'max_sync_load_schedule'):
            
                #t.resource.scheduler.max_sync_load_schedules[1] = None
                #t.resource.scheduler.max_sync_load_schedules[1] = None
                    
                if last_resource == None:
                    t.resource.scheduler.max_sync_load_schedules[1] = None
                else:
                    if not last_resource == t.resource:
                        t.resource.scheduler.max_sync_load_schedules[1] = None
                        
                                        
            analysis_state.dirtyTasks.remove(t)

            # skip analysis for tasks w/ disable propagation
            if t.skip_analysis:
                continue

            if only_dependent_tasks and len(analysis_state.
                                            dependentTask[t]) == 0:
                continue  # skip analysis of tasks w/o dependents

            old_jitter = task_results[t].wcrt - task_results[t].bcrt
            old_busytimes = copy.copy(task_results[t].busy_times)
            analyze_task(t, task_results)

            #sanity check
            if not t.resource.scheduler.is_sync_task(t):
                assert functools.reduce(lambda x, y: x and y,\
                               [b - a >= t.wcet for a,b \
                                in util.window(task_results[t].busy_times)]) == True, "Busy_times for task %s on resource %s: %s" % (t.name, t.resource.name, str(task_results[t].busy_times))

            new_jitter = task_results[t].wcrt - task_results[t].bcrt
            new_busytimes = task_results[t].busy_times

            if new_jitter != old_jitter or old_busytimes != new_busytimes:
                # If jitter has changed, the input event models of all
                # dependent task(s) have also changed,
                # including their dependent tasks and so forth...
                # so mark them and all other tasks on their resource for
                # another analysis

                # propagate event model
                pycpa_analysis._propagate(t, task_results)

                # mark all dependencies dirty
                analysis_state._mark_dependents_dirty(t)
                
                
                                
                for dtask in analysis_state.dependentTask[t]:
                    if isinstance(dtask.in_event_model, composed_model.SyncComposedEventModel) or isinstance(dtask.in_event_model, composed_propagation.SyncComposedPropagationEventModel):
                        if dtask.scheduling_parameter in dtask.resource.scheduler.max_sync_load_schedules:
                            dtask.resource.scheduler.max_sync_load_schedules[dtask.scheduling_parameter] = None
                            
                                
                break  # break the for loop to restart iteration

            elapsed = (timefunc() - start)
            logger.debug("iteration: %d, time: %.1f task: %s wcrt: %f dirty: %d"
                         % (iteration, elapsed, t.name,
                            task_results[t].wcrt,
                            len(analysis_state.dirtyTasks)))
            if elapsed > options.get_opt('timeout'):
                raise pycpa_analysis.TimeoutException("Timeout reached after iteration %d" % iteration)
            iteration += 1

        elapsed = timefunc() - start
        if elapsed > options.get_opt('timeout'):
            raise pycpa_analysis.TimeoutException("Timeout reached after iteration %d" % iteration)

        # # check for constraint violations
        if options.get_opt("check_violations"):
            violations = pycpa_analysis.check_violations(system.constraints, task_results)
            if violations == True:
                logger.error("Analysis stopped!")
                raise pycpa_analysis.NotSchedulableException("Violation of constraints")
                break

    # # also print the violations if on-the-fly checking was turned off
    if not options.get_opt("check_violations"):
        pycpa_analysis.check_violations(system.constraints, task_results)
    
    # a hook that allows to inspect the analysis_state object after the analysis run
    post_hook = kwargs.get('post_hook', None)
    if post_hook is not None:
        post_hook(analysis_state)

    return task_results





