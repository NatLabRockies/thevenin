from __future__ import annotations
from typing import Iterable, Callable, TypeVar, TYPE_CHECKING

import textwrap
from copy import deepcopy

import atexit
import numpy as np
import matplotlib.pyplot as plt

from .solvers import IDAResult

if TYPE_CHECKING:  # pragma: no cover
    from ._simulation import Simulation

    Solution = TypeVar('Solution', bound='BaseSolution')

if not hasattr(np, 'concat'):  # pragma: no cover
    np.concat = np.concatenate


class ExitHandler:
    """
    Exit handler.

    Use this class to register functions that you want to run just before a
    file exits. This is primarily used to register plt.show() so plots appear
    in both interactive and non-interactive environments, even if the user
    forgets to explicitly call it.

    """

    _registered = []

    @classmethod
    def register_atexit(cls, func: Callable) -> None:
        if func not in cls._registered:
            atexit.register(func)


class BaseSolution(IDAResult):
    """Base solution."""

    def __init__(self) -> None:
        """
        The base solution class is a parent class to both the StepSolution
        and CycleSolution classes. Inheriting from this class gives each
        solution instance a 'vars' dictionary, access to the 'plot' method,
        and ensures that the slicing of the solution vector into 'vars' is
        consistent between all solutions.

        """
        self.vars = {}

    def __repr__(self) -> str:  # pragma: no cover
        """
        Return a readable repr string.

        Returns
        -------
        readable : str
            A console-readable instance representation.

        """
        classname = self.__class__.__name__

        def wrap_string(label: str, value: list, width: int):
            if isinstance(value, Iterable):
                value = list(value)
            else:
                value = [value]

            indent = ' '*(len(label) + 1)

            if classname == 'StepSolution' and len(value) == 1:
                text = label + f"{value[0]!r}"
            else:
                text = label + "[" + ", ".join(f"{v!r}" for v in value) + "]"

            return textwrap.fill(text, width=width, subsequent_indent=indent)

        data = [
            wrap_string('    success=', self.success, 79),
            wrap_string('    status=', self.status, 79),
            wrap_string('    nfev=', self.nfev, 79),
            wrap_string('    njev=', self.njev, 79),
            wrap_string('    vars=', self.vars.keys(), 79),
        ]

        summary = f"    solvetime={self.solvetime},"
        for d in data:
            summary += f"\n{d},"

        readable = f"{classname}(\n{summary}\n)"

        return readable

    def plot(self, x: str, y: str, **kwargs) -> None:
        """
        Plot any two variables in 'vars' against each other.

        Parameters
        ----------
        x : str
            A variable key in 'vars' to be used for the x-axis.
        y : str
            A variable key in 'vars' to be used for the y-axis.
        **kwargs : dict, optional
            Keyword arguments to pass through to `plt.plot()`. For more info
            please refer to documentation for `maplotlib.pyplot.plot()`.

        Returns
        -------
        None.

        """
        plt.figure()
        plt.plot(self.vars[x], self.vars[y], **kwargs)

        if '_' in x:
            variable, units = x.split('_')
            xlabel = variable.capitalize() + ' [' + units + ']'
        else:
            xlabel = x

        if '_' in y:
            variable, units = y.split('_')
            ylabel = variable.capitalize() + ' [' + units + ']'
        else:
            ylabel = y

        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        if not plt.isinteractive():
            ExitHandler.register_atexit(plt.show)

    def _fill_vars(self) -> None:
        """
        Fills the 'vars' dictionary by slicing the SolverReturn solution
        states. Users should generally only access the solution via 'vars'
        since names are more intuitive than interpreting 'y' directly.

        Returns
        -------
        None.

        """
        from ._basemodel import calculated_current

        sim = self._sim
        ptr = sim._ptr

        time = self.t

        soc = self.y[:, ptr['soc']]
        T_cell = self.y[:, ptr['T_cell']]*sim._T_ref
        hyst = self.y[:, ptr['hyst']]
        eta_j = self.y[:, ptr['eta_j']]
        voltage = self.y[:, ptr['V_cell']]

        try:
            ocv = sim.ocv(soc)
            R0 = sim.R0(soc, T_cell)

            assert isinstance(ocv, np.ndarray)
            assert isinstance(R0, np.ndarray)
            assert ocv.shape == soc.shape
            assert R0.shape == soc.shape

        except (TypeError, AssertionError):

            ocv = np.empty_like(soc)
            R0 = np.empty_like(soc)
            for i in range(soc.size):
                ocv[i] = sim.ocv(soc[i])
                R0[i] = sim.R0(soc[i], T_cell[i])

        current = calculated_current(voltage, ocv, hyst, eta_j, R0)

        # stored time
        self.vars['time_s'] = time
        self.vars['time_min'] = time / 60.
        self.vars['time_h'] = time / 3600.

        # from state variables
        self.vars['soc'] = soc
        self.vars['temperature_K'] = T_cell
        self.vars['voltage_V'] = voltage
        self.vars['hysteresis_V'] = hyst

        # post-processed variables
        self.vars['current_A'] = current
        self.vars['power_W'] = current*voltage
        self.vars['eta0_V'] = current*R0

        for j, eta in enumerate(eta_j.T, start=1):
            self.vars['eta' + str(j) + '_V'] = eta


class StepSolution(BaseSolution):
    """Single-step solution."""

    def __init__(self, sim: Simulation, ida_soln: IDAResult,
                 timer: float) -> None:
        """
        A solution instance for a single experimental step.

        Parameters
        ----------
        sim : Simulation
            The simulation instance that was run to produce the solution.
        ida_soln : IDAResult
            The unformatted solution returned by IDASolver.
        timer : float
            Amount of time it took for IDASolver to perform the integration.

        """
        super().__init__()

        self._sim = deepcopy(sim)

        self.message = ida_soln.message
        self.success = ida_soln.success
        self.status = ida_soln.status

        self.t = ida_soln.t
        self.y = ida_soln.y
        self.yp = ida_soln.yp

        self.i_events = ida_soln.i_events
        self.t_events = ida_soln.t_events
        self.y_events = ida_soln.y_events
        self.yp_events = ida_soln.yp_events

        self.nfev = ida_soln.nfev
        self.njev = ida_soln.njev

        self._timer = timer

        self._fill_vars()

    @property
    def solvetime(self) -> str:
        """
        Print a statement specifying how long IDASolver spent integrating.

        Returns
        -------
        solvetime : str
            An f-string with the solver integration time in seconds.

        """
        return f"{self._timer:.3f} s"


class CycleSolution(BaseSolution):
    """All-step solution."""

    def __init__(self, *soln: StepSolution, t_shift: float = 1e-3) -> None:
        """
        A solution instance with all experiment steps stitch together into
        a single cycle.

        Parameters
        ----------
        *soln : StepSolution
            All unpacked StepSolution instances to stitch together. The given
            steps should be given in the same sequential order that they were
            run.
        t_shift : float
            Time (in seconds) to shift step solutions by when stitching them
            together. If zero the end time of each step overlaps the starting
            time of its following step. The default is 1e-3.

        """
        super().__init__()

        soln = deepcopy(list(soln))  # ensure type list, memory safe copy

        self._solns = soln
        self._sim = soln[0]._sim

        t_size = np.sum([soln.t.size for soln in self._solns])
        sv_size = self._sim._sv0.size

        self.message = []
        self.success = []
        self.status = []

        self.t = np.empty([t_size])
        self.y = np.empty([t_size, sv_size])
        self.yp = np.empty([t_size, sv_size])

        self.t_events = None
        self.y_events = None
        self.yp_events = None

        self.nfev = []
        self.njev = []

        self._timers = []

        first = 0
        for soln in self._solns:
            soln_size = soln.t.size
            last = first + soln_size

            if first > 0:
                shift_t = self.t[first - 1] + soln.t + t_shift
            else:
                shift_t = soln.t

            if soln.t_events is not None and first > 0:
                shift_t_events = self.t[first - 1] + soln.t_events + t_shift
            elif soln.t_events is not None:
                shift_t_events = soln.t_events

            self.message.append(soln.message)
            self.success.append(soln.success)
            self.status.append(soln.status)

            self.t[first:last] = shift_t
            self.y[first:last, :] = soln.y
            self.yp[first:last, :] = soln.yp

            first = last

            if soln.t_events is not None:
                if self.t_events is None:
                    self.t_events = shift_t_events
                    self.y_events = soln.y_events
                    self.yp_events = soln.yp_events
                else:
                    self.t_events = np.concat([self.t_events, shift_t_events])
                    self.y_events = np.concat([self.y_events, soln.y_events])
                    self.yp_events = np.concat([self.yp_events, soln.yp_events])

            self.nfev.append(soln.nfev)
            self.njev.append(soln.njev)

            self._timers.append(soln._timer)

        self._fill_vars()

    @property
    def solvetime(self) -> str:
        """
        Print a statement specifying how long IDASolver spent integrating.

        Returns
        -------
        solvetime : str
            An f-string with the total solver integration time in seconds.

        """
        return f"{sum(self._timers):.3f} s"

    def get_steps(self, idx: int | tuple) -> StepSolution | CycleSolution:
        """
        Return a subset of the solution.

        Parameters
        ----------
        idx : int | tuple
            The step index (int) or range (first, last) to return.

        Returns
        -------
        :class:`StepSolution` | :class:`CycleSolution`
            The returned solution subset. A StepSolution is returned if 'idx'
            is an int, and a CycleSolution will be returned for the range of
            requested steps when 'idx' is a tuple.

        """
        if isinstance(idx, int):
            return deepcopy(self._solns[idx])
        elif isinstance(idx, (tuple, list)):
            solns = self._solns[idx[0]:idx[1] + 1]
            return CycleSolution(*solns)

    def append_soln(self, soln: Solution, t_shift: float = 1e-3) -> None:
        """
        Append another solution object to the current instance. Appending the
        instance itself is also allowed, which is helpful to visualize multiple
        cycles.

        Parameters
        ----------
        soln : StepSolution | CycleSolution
            A solution (step or cycle) to append to the end of the current
            instance.
        t_shift : float, optional
            Time (in seconds) to add between the current solution and new
            appended solution. If zero, the current final time and new initial
            time will exactly overlap. The default is 1e-3.

        Returns
        -------
        None.

        Raises
        ------
        TypeError
            'soln' input must be StepSolution, CycleSolution.
        ValueError
            'soln' input is incompatible because it came from a simulation with
            different num_RC_pairs.

        Notes
        -----
        The `t_shift` input only affects the shift between the current and
        new solutions. For example if two `CycleSolution` had original shifts
        of 1 and 5 for their respective steps when stitched, this appended case
        will still have 1 for the first few steps, `t_shift` between, and 5
        for the shifts between the latter half's steps.

        Appending solutions cannot simply be undone. If you think you may want
        to go back to an instance prior to appending another solution then you
        should create a copy to operate on. Use `copy.deepcopy` from Python's
        standard library to make sure the copy is memory safe, i.e., the two
        instances do not share any common memory.

        """
        if not isinstance(soln, (StepSolution, CycleSolution)):
            raise TypeError("'soln' input must be StepSolution, CycleSolution.")

        if self._sim.num_RC_pairs != soln._sim.num_RC_pairs:
            raise ValueError("'soln' input is incompatible because it came"
                             " from a simulation with different num_RC_pairs.")

        soln = deepcopy(soln)

        shift_t = self.t[-1] + soln.t + t_shift
        if soln.t_events is not None:
            shift_t_events = self.t[-1] + soln.t_events + t_shift

        if isinstance(soln, StepSolution):
            self._solns.append(soln)

            self.message.append(soln.message)
            self.success.append(soln.success)
            self.status.append(soln.status)

            self.nfev.append(soln.nfev)
            self.njev.append(soln.njev)

            self._timers.append(soln._timer)

        elif isinstance(soln, CycleSolution):
            self._solns.extend(soln._solns)

            self.message.extend(soln.message)
            self.success.extend(soln.success)
            self.status.extend(soln.status)

            self.nfev.extend(soln.nfev)
            self.njev.extend(soln.njev)

            self._timers.extend(soln._timers)

        self.t = np.concat([self.t, shift_t])
        self.y = np.concat([self.y, soln.y])
        self.yp = np.concat([self.yp, soln.yp])

        if soln.t_events is not None:
            if self.t_events is None:
                self.t_events = shift_t_events
                self.y_events = soln.y_events
                self.yp_events = soln.yp_events
            else:
                self.t_events = np.concat([self.t_events, shift_t_events])
                self.y_events = np.concat([self.y_events, soln.y_events])
                self.yp_events = np.concat([self.yp_events, soln.yp_events])

        self._fill_vars()
