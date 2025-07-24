"""
| Copyright (C) 2020-2025 Jonas Peeck
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Jonas Peeck

Description
-----------

Definition of Cross Layer Model edges.
"""


# ----------------------------------------------------------------------------------
# ---------------------------------- Link classes ----------------------------------
# ----------------------------------------------------------------------------------
class Link(object):
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

class Ethernet_Connection(Link):
    def __init__(self, c1, c2, **kwargs):
        super().__init__(**kwargs)
        # Storing the connections
        self.c1 = c1
        self.c2 = c2

class Link_TaskPrecedence(Link):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

# -----------------------------------------------------------------------------------
# --------------------------------- Mapping classes ---------------------------------
# -----------------------------------------------------------------------------------


class Mapping(object):
    """ Base class for bidirectional links of elements of different layers """

    def __init__(self, **kwargs):
        self.name = ''
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __repr__(self):
        return self.name

class Mapping_TaskToExecUnit(Mapping):
    """ Bidirectional mapping of a Task and a Processing Unit """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Mapping_SwitchToExecUnit(Mapping):
    """ Bidirectional mapping of a Switch to an ExecUnit """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Mapping_NICEndpointToExecUnit(Mapping):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Mapping_StreamInputModelToEthernetStream(Mapping):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Mapping_StreamInputModelToEthernetEventSource(Mapping):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Mapping_DDSStreamInputModelToEthernetEventSource(Mapping):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Mapping_TaskToEthernetEventSource(Mapping):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)



