from __future__ import annotations
from typing import TypeVar, TYPE_CHECKING

import time
from copy import deepcopy

import numpy as np

from thevenin._basemodel import BaseModel

if TYPE_CHECKING:  # pragma: no cover
    from ._experiment import Experiment
    from ._prediction import Prediction, TransientState
    from ._solutions import BaseSolution, StepSolution, CycleSolution

    Solution = TypeVar('Solution', bound='BaseSolution')


class Simulation(BaseModel):
    """
    Simulation model wrapper.

    This class is primarily intended for full timeseries simulations. Use the
    :class:`~thevenin.Experiment` class to provide the details of an experiment.
    Note that this version of the model interface manages its own internal
    state. The user has limited ability to directly control the state. At the
    beginning of all simulations, the model is assumed in a fully rested state
    at the user-supplied state-of-charge `soc0`. Through the pre-processor
    method `pre()` you can manually force the state to start at a value given
    a previous solution, or using a :class:`~thevenin.TransientState` instance
    for maximum control.

    """

    def pre(self, state0: bool | Solution | TransientState = True) -> None:
        """
        Pre-process and prepare the model for running experiments.

        This method builds solution pointers, registers algebraic variable
        indices, stores the mass matrix, and initializes the hidden state.

        Parameters
        ----------
        state0 : bool | Solution | TransientState
            Control how the model state is initialized. If True (default), the
            state is set to a rested condition at 'soc0'. If False, the state
            is left alone and only internal checks are run. Given a Solution
            instance, the state is set to the final state of the solution. See
            the notes for more information.

        Returns
        -------
        None.

        Notes
        -----
        This method runs during the class initialization. It generally does not
        have to be run again unless you want to reset the internal hidden state.
        Using the `state0` argument, you can set the state back to a rested
        condition at 'soc0', to the final value from a `Solution`, or to a
        user-defined state given by a `TransientState` instance.

        When initializing based on a Solution instance, the solution must be
        the same size as the current model. In other words, a 1RC-pair model
        cannot be initialized by a solution from a 2RC-pair circuit. Similarly,
        the eta_j size from a TransientState instance must match the size of
        RC pairs in the current model.

        """
        from ._solutions import BaseSolution
        from ._prediction import TransientState

        self._check_RC_pairs()  # inherited from BaseModel

        ptr = {}
        ptr['soc'] = 0
        ptr['T_cell'] = 1
        ptr['hyst'] = 2
        ptr['eta_j'] = np.arange(3, 3 + self.num_RC_pairs)
        ptr['V_cell'] = self.num_RC_pairs + 3
        ptr['size'] = self.num_RC_pairs + 4

        algidx = [ptr['V_cell']]

        mass_matrix = np.ones(ptr['size'])
        mass_matrix[ptr['V_cell']] = 0.

        sv0 = np.zeros(ptr['size'])
        sv0[ptr['soc']] = self.soc0
        sv0[ptr['T_cell']] = self.T_inf / self._T_ref
        sv0[ptr['hyst']] = 0.
        sv0[ptr['eta_j']] = 0.
        sv0[ptr['V_cell']] = self.ocv(self.soc0)

        svdot0 = np.zeros_like(sv0)

        self._ptr = ptr
        self._algidx = algidx
        self._mass_matrix = mass_matrix

        self._t0 = 0.
        if isinstance(state0, BaseSolution):
            soln = deepcopy(state0)
            if soln.y[-1].size != sv0.size:
                raise ValueError("Cannot initialize state based on Solution"
                                 " object given in 'state0'. The model and"
                                 " solution have incompatible sizes.")

            self._sv0 = soln.y[-1]
            self._svdot0 = soln.yp[-1]

        elif isinstance(state0, TransientState):
            state0 = deepcopy(state0)
            if state0.num_RC_pairs != self.num_RC_pairs:
                raise ValueError("Cannot initialize state from TransientState"
                                 " object given in 'state0'. The model and"
                                 " solution have incompatible sizes.")

            sv0[ptr['soc']] = state0.soc
            sv0[ptr['T_cell']] = state0.T_cell / self._T_ref
            sv0[ptr['hyst']] = state0.hyst
            sv0[ptr['eta_j']] = state0.eta_j
            sv0[ptr['V_cell']] = self.ocv(state0.soc)

            self._sv0 = sv0
            self._svdot0 = svdot0

        elif state0:
            self._sv0 = sv0
            self._svdot0 = svdot0

    def run_step(self, expr: Experiment, stepidx: int) -> StepSolution:
        """
        Run a single experimental step.

        Parameters
        ----------
        expr : Experiment
            An experiment instance.
        stepidx : int
            Step index to run. The first step has index 0.

        Returns
        -------
        :class:`~thevenin.StepSolution`
            Solution to the experimental step.

        Warning
        -------
        The model's internal state is changed at the end of each experimental
        step. Consequently, you should not run steps out of order. You should
        always start with `stepidx = 0` and then progress to the subsequent
        steps afterward. If at any time you want to reset the internal hidden
        state back to a rested condition, use `pre()`.

        See Also
        --------
        Experiment : Build an experiment.
        StepSolution : Wrapper for a single-step solution.

        Notes
        -----
        Using `run()` loops through all steps in an experiment and stitches
        their solutions together. Most of the time, this is more convenient.
        However, running step-by-step provides maximum control to fine tune
        solver options. It also allows for complex analyses and/or control
        decisions to be performed between experimental steps.

        """
        from .solvers import IDASolver
        from ._solutions import StepSolution

        step = expr.steps[stepidx].copy()
        kwargs = expr._kwargs[stepidx].copy()

        if not callable(step['value']):
            value = step['value']
            step['value'] = lambda t: value

        kwargs['userdata'] = step
        kwargs['calc_initcond'] = 'yp0'
        kwargs['algebraic_idx'] = self._algidx

        if step['limits'] is not None:
            _setup_eventsfn(step['limits'], kwargs)

        solver = IDASolver(self._resfn, **kwargs)

        start = time.time()
        ida_soln = solver.solve(step['tspan'], self._sv0, self._svdot0)
        timer = time.time() - start

        soln = StepSolution(self, ida_soln, timer)

        self._t0 = soln.t[-1]
        self._sv0 = soln.y[-1].copy()
        self._svdot0 = soln.yp[-1].copy()

        return soln

    def run(self, expr: Experiment, reset_state: bool = True,
            t_shift: float = 1e-3) -> CycleSolution:
        """
        Run a full experiment.

        Parameters
        ----------
        expr : Experiment
            An experiment instance.
        reset_state : bool
            If True (default), the internal state of the model will be reset
            back to a rested condition at 'soc0' at the end of all steps. When
            False, the state does not reset. Instead it will update to match
            the final state of the last experimental step.
        t_shift : float
            Time (in seconds) to shift step solutions by when stitching them
            together. If zero the end time of each step overlaps the starting
            time of its following step. The default is 1e-3.

        Returns
        -------
        :class:`~thevenin.CycleSolution`
            A stitched solution with all experimental steps.

        Warning
        -------
        The default behavior resets the model's internal state back to a rested
        condition at 'soc0' by calling the `pre()` method at the end of all
        steps. This means that if you run a second experiment afterward, it
        will not start where the previous one left off. Instead, it will start
        from the original rested condition that the model initialized with. You
        can bypass this by using `reset_state=False`, which keeps the state
        at the end of the final experimental step.

        See Also
        --------
        Experiment : Build an experiment.
        CycleSolution : Wrapper for an all-steps solution.

        """
        from ._solutions import CycleSolution

        solns = []
        for i in range(expr.num_steps):
            solns.append(self.run_step(expr, i))

        soln = CycleSolution(*solns, t_shift=t_shift)

        self._t0 = 0.
        if reset_state:
            self.pre()

        return soln

    def to_prediction(self) -> Prediction:
        """
        Generate a `Prediction` class instance with the same properties as
        the current `Simulation`.

        Returns
        -------
        :class:`~thevenin.Prediction`
            An instance of the Prediction interface, initialized with the same
            properties as the current Simulation instance.

        """
        from ._prediction import Prediction

        return Prediction(self._get_params_dict)

    def _resfn(self, t: float, sv: np.ndarray, svdot: np.ndarray,
               res: np.ndarray, userdata: dict) -> None:
        """
        Solver-structured residuals.

        The IDASolver requires a residuals function in this exact form.
        Rather than outputting the residuals, the function returns None,
        but fills the 'res' input array with the DAE residuals.

        Parameters
        ----------
        t : float
            Value of time [s].
        sv : 1D np.array
            State variables at time t.
        svdot : 1D np.array
            State variable time derivatives at time t.
        res : 1D np.array
            DAE residuals, res = M*yp - rhs(t, y).
        userdata : dict
            Dictionary detailing an experimental step.

        Returns
        -------
        None.

        """
        res[:] = self._mass_matrix*svdot - self._rhsfn(t, sv, userdata)


class _EventsFunction:
    """Event function callables."""

    def __init__(self, limits: tuple[str, float]) -> None:
        """
        A generalized event function callable.

        Parameters
        ----------
        limits : tuple[str, float]
            A tuple of event function criteria arranged as ordered pairs of
            limit names and values, e.g., ('time_h', 10., 'voltage_V', 4.2).

        """
        self.keys = limits[0::2]
        self.values = limits[1::2]
        self.size = len(self.keys)

    def __call__(self, t: float, sv: np.ndarray, svdot: np.ndarray,
                 events: np.ndarray, userdata: dict) -> None:
        """
        Solver-structured event function.

        The IDASolver requires a event function in this exact form. Rather
        than outputting the events array, the function returns None, but
        fills the 'events' input array with event functions. If any 'events'
        index equals zero, the solver will exit prior to 'tspan[-1]'.

        Parameters
        ----------
        t : float
            Value of time [s].
        sv : 1D np.array
            State variables at time t.
        svdot : 1D np.array
            State variable time derivatives at time t.
        events : 1D np.array
            An array of event functions. During integration, the solver will
            exit prior to 'tspan[-1]' if any 'events' index equals zero.
        userdata : dict
            Dictionary detailing an experimental step, with the 'events' key
            added and filled within the `rhs_funcs()' method.

        Returns
        -------
        None.

        """
        for i, (key, value) in enumerate(zip(self.keys, self.values)):
            events[i] = userdata['events'][key] - value


def _setup_eventsfn(limits: tuple[str, float], kwargs: dict) -> None:
    """
    Set up a event function for the IDASolver.

    The IDASolver requires two keyword arguments to be set when using event
    functions. The first is 'eventsfn' which requires a Callable. The second
    is 'num_events' with allocates memory to an array that stores the event
    function values.

    Parameters
    ----------
    limits : tuple[str, float]
        A tuple of event function criteria arranged as ordered pairs of limit
        names and values, e.g., ('time_h', 10., 'voltage_V', 4.2).
    kwargs : dict
        The IDASolver keyword argumnents dictionary. Both the 'eventsfn' and
        'num_events' keyword arguments must be added to 'kwargs'.

    Returns
    -------
    None.

    """
    eventsfn = _EventsFunction(limits)

    kwargs['eventsfn'] = eventsfn
    kwargs['num_events'] = eventsfn.size
