"""
The `loadfns` module contains classes to construct time-varying load profiles.
All of the classes are callable after construction and take in a value of
time in seconds. Most load functions include a linear ramp that "smooths"
transitions from rest to a constant load, or between constant steps. Using
ramps helps the solver maintain stability when a boundary condition sharply
changes from one value to another, e.g., jumping from rest into a high-rate
charge or discharge. For example, in some cases the solver may crash for a
high-rate discharge.

"""

from ._ramps import Ramp, Ramp2Constant
from ._steps import StepFunction, RampedSteps

__all__ = [
    'Ramp',
    'Ramp2Constant',
    'StepFunction',
    'RampedSteps',
]
