from __future__ import annotations
from typing import Callable, TypeVar, TYPE_CHECKING

import numpy as np

from thevenin._basemodel import BaseModel

if TYPE_CHECKING:  # pragma: no cover
    from ._simulation import Simulation
    from ._solutions import BaseSolution

    Solution = TypeVar('Solution', bound='BaseSolution')


class TransientState:
    """Transient state for predictions."""

    def __init__(self, soc: float, T_cell: float, hyst: float,
                 eta_j: np.ndarray | None) -> None:
        """
        A container that allows users to manage the internal hidden states of
        model classes. Users only have control over independent state variables
        (i.e., soc, T_cell, hyst, eta_j). The :class:`~thevenin.Prediction`
        interface requires an instance of the `TransientState` each time a
        prediction step is made. You can optionally use instances of this class
        to define the starting state of :class:`~thevenin.Simulation` instances
        using their `pre()` method. In general, however, the model interface
        for simulations is more limited when it comes to user-defined states.

        The read-only `voltage` property will return None if the state was
        user defined. If instead the state was returned by the `Prediction`
        class, the value will be the predicted voltage after a given step.

        Parameters
        ----------
        soc : float
            State of charge [-].
        T_cell : float
            Temperature of the cell [K].
        hyst : float
            Hysteresis voltage [V].
        eta_j : 1D np.array | None
            RC pair overpotentials [V].

        See Also
        --------
        Simulation : The model wrapper used for timeseries simulations.
        Prediction : The model wrapper used for step-by-step predictions.

        """
        self.soc = soc
        self.T_cell = T_cell
        self.hyst = hyst

        if eta_j is None:
            self.eta_j = np.array([])
        else:
            self.eta_j = np.asarray(eta_j)

        self._voltage = None

        self._repr_keys = [
            'soc',
            'T_cell',
            'hyst',
            'eta_j',
        ]

    def __repr__(self) -> str:  # pragma: no cover
        """
        Return a readable repr string.

        Returns
        -------
        readable : str
            A console-readable instance representation.

        """
        keys = self._repr_keys
        values = [getattr(self, k) for k in keys]

        summary = "\n    ".join([f"{k}={v}," for k, v in zip(keys, values)])
        readable = f"TransientState(\n    {summary}\n)"

        return readable

    @property
    def num_RC_pairs(self) -> int:
        """Number of RC pairs in the circuit."""
        return len(self.eta_j)

    @property
    def voltage(self) -> float | None:
        """None if user-defined state. Otherwise, predicted voltage [V]."""
        return self._voltage

    def _set_voltage(self, voltage: float) -> None:
        """A hidden method for the 'Prediction' class to set the voltage."""
        self._voltage = voltage


class Prediction(BaseModel):
    """
    Prediction model wrapper.

    This class is primarily intended for prediction-correction algorithms,
    e.g., Kalman filters. The interface is set up to let the user manage the
    internal state via the :class:`~thevenin.TransientState` class. In addition,
    the model is only designed to run current-based loads in a step-by-step
    fashion. If you are looking to simulate more complex protocols and use the
    resulting timeseries data you should use the :class:`~thevenin.Simulation`
    class instead.

    Note that this class and the :class:`~thevenin.Simulation` class share the
    same `params` inputs. This is for convenience so that users can easily
    switch between the two. However, the 'soc0' value has no real meaning for
    the prediction interface. Instead, the user manages the state of charge for
    each step through the `TransientState` interface. This means that you can
    effectively ignore the 'soc0' input when using this class.

    """

    def pre(self) -> None:
        """
        Pre-process and prepare the model to make predictions. Specifically,
        this method builds pointers so it can manage mapping the state back
        and forth between the solver-required array format and the user-managed
        `TransientState` class.

        Returns
        -------
        None.

        Notes
        -----
        This method runs during the class initialization. It generally does not
        have to be run again unless you want to re-run internal checks on the
        class instance.

        """
        self._check_RC_pairs()  # inherited from BaseModel

        ptr = {}
        ptr['soc'] = 0
        ptr['T_cell'] = 1
        ptr['hyst'] = 2
        ptr['eta_j'] = np.arange(3, 3 + self.num_RC_pairs)
        ptr['size'] = self.num_RC_pairs + 3

        self._ptr = ptr

        self.set_options()

    def set_options(self, **options) -> None:
        """
        Set the solver options for the underlying ODE integrator.

        Parameters
        ----------
        **options : dict, optional
            CVODESolver keyword arguments that span all steps. You can re-run
            this method between prediction steps if you need different settings
            per step.

        See Also
        --------
        ~thevenin.solvers.CVODESolver :
            The solver class, with documentation for most keyword arguments
            that you might want to adjust.

        """
        from .solvers import CVODESolver

        self._userdata = {}
        options = {'userdata': self._userdata, **options}
        self._solver = CVODESolver(self._svdot, **options)

    def take_step(self, state: TransientState, current: float | Callable,
                  delta_t: float) -> TransientState:
        """
        Take a step forward in time to predict the new state and voltage given
        a starting state, demand current, and time step.

        Parameters
        ----------
        state : TransientState
            Description of the starting state.
        current : float | Callable
            Demand current [A]. For a dynamic current, use a callable with a
            signature like `def current(t: float) -> float`, where the input
            time is in seconds relative to the overall step.
        delta_t : float
            Magnitude of time step, in seconds.

        Returns
        -------
        :class:`~thevenin.TransientState`
            Predicted state at the end of the time step.

        """
        if callable(current):
            self._userdata['current'] = current
        else:
            self._userdata['current'] = lambda t: current

        sv0 = self._to_array(state)

        _ = self._solver.init_step(0., sv0)
        soln = self._solver.step(delta_t)

        # state prediction
        state = self._to_state(soln.y)

        # voltage prediction
        ocv = self.ocv(state.soc)
        R0 = self.R0(state.soc, state.T_cell)

        current = self._userdata['current'](soln.t)
        voltage = ocv + state.hyst - np.sum(state.eta_j) - current*R0

        state._set_voltage(voltage)

        return state

    def to_simulation(
        self, state0: bool | Solution | TransientState = True,
    ) -> Simulation:
        """
        Generate a `Simulation` class instance with the same properties as
        the current `Prediction`.

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
        :class:`~thevenin.Simulation`
            An instance of the Simulation interface, initialized with the same
            properties as the current Prediction instance.

        Notes
        -----
        When initializing based on a Solution instance, the solution must be
        the same size as the current model. In other words, a 1RC-pair model
        cannot be initialized by a solution from a 2RC-pair circuit. Similarly,
        the eta_j size from a TransientState instance must match the size of
        RC pairs in the current model.

        """
        from ._simulation import Simulation

        sim = Simulation(self._get_params_dict)
        sim.pre(state0)

        return sim

    def _to_state(self, array: np.ndarray) -> TransientState:
        """
        Map an array returned by the solver to a 'TransientState' instance.

        Parameters
        ----------
        array : 1D np.array
            State variables array compatible with the solver..

        Returns
        -------
        :class:`~thevenin.TransientState`
            Human-interpretable instance of the state variables array.

        """
        ptr = self._ptr.copy()
        _ = ptr.pop('size')

        state = {}
        for k, v in ptr.items():
            state[k] = array[v] * (self._T_ref if k == 'T_cell' else 1.)

        return TransientState(**state)

    def _to_array(self, state: TransientState) -> np.ndarray:
        """
        Map a 'TransientState' instance to a numpy array for the solver.

        Parameters
        ----------
        state : TransientState
            Human-interpretable instance of the state variables array.

        Returns
        -------
        array : 1D np.array
            State variables array compatible with the solver.

        Raises
        ------
        ValueError
            state.eta_j has an invalid length. The number of overpotentials
            must be consistent with the model's 'num_RC_pairs' attribute.

        """
        if state.num_RC_pairs != self.num_RC_pairs:
            raise ValueError(f"{state.eta_j=} has an invalid length since"
                             f" num_RC_pairs={self.num_RC_pairs}.")

        ptr = self._ptr.copy()
        size = ptr.pop('size')

        sv = np.zeros(size)
        for k, v in ptr.items():
            sv[v] = getattr(state, k) / (self._T_ref if k == 'T_cell' else 1.)

        return sv

    def _svdot(self, t: float, sv: np.ndarray, svdot: np.ndarray,
               userdata: dict) -> None:
        """
        Solver-structured right-hand-side.

        The CVODESolver requires a right-hand-side function in this form.
        Rather than outputting the derivatives, the function returns None,
        but fills the 'svdot' input array with the ODE expressions.

        Parameters
        ----------
        t : float
            Value of time [s].
        sv : 1D np.array
            State variables at time t.
        svdot : 1D np.array
            State variable time derivatives from ODEs, svdot = rhs(t, sv).
        userdata : dict
            Dictionary detailing an experimental step.

        Returns
        -------
        None.

        """
        svdot[:] = self._rhsfn(t, sv, userdata)
