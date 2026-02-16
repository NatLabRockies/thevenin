"""
Summary
=======
The Thevenin equivalent circuit model is a common low-fidelity battery model
consisting of a single resistor in series with any number of RC pairs, i.e.,
parallel resistor-capacitor pairs. This Python package contains an API for
building and running experiments using Thevenin models. When referring to the
model itself, we use capitalized "Thevenin", and for the package lowercase
`thevenin`.

Accessing the Documentation
---------------------------
Documentation is accessible via Python's `help()` function which prints
docstrings from a package, module, function, class, etc. You can also access
the documentation by visiting the website, hosted on Read the Docs. The website
includes search functionality and more detailed examples.

"""

# core package
from ._experiment import Experiment
from ._simulation import Simulation
from ._prediction import TransientState, Prediction
from ._solutions import StepSolution, CycleSolution
from ._templates import (
    download_templates, list_templates, load_templates, print_templates,
)

# submodules
from . import loadfns
from . import plotutils
from . import solvers

__version__ = '0.3.0.dev0'

__all__ = [
    'Experiment',
    'Simulation',
    'TransientState',
    'Prediction',
    'StepSolution',
    'CycleSolution',
    'download_templates',
    'list_templates',
    'load_templates',
    'print_templates',
    'loadfns',
    'plotutils',
    'solvers',
]


class Model(Simulation):  # pragma: no cover

    def __init__(self, params='params.yaml'):
        from warnings import warn

        warn("The 'Model' class has been renamed 'Simulation'. In a future"
             " release 'Model' will be deprecated.", DeprecationWarning,
             stacklevel=2)

        super().__init__(params)
