from __future__ import annotations

import numpy as np

if not hasattr(np, 'concat'):  # pragma: no cover
    np.concat = np.concatenate


class StepFunction:
    """Piecewise step function."""

    __slots__ = ('_tp', '_yp', '_func',)

    def __init__(self, tp: np.ndarray, yp: np.ndarray, y0: float = 0.,
                 ignore_nan: bool = False) -> None:
        """
        Construct a piecewise step function given the times at which step
        changes occur and the values for each time interval.

        .. code-block:: python

            tp = np.array([0, 5])
            yp = np.array([-1, 1])

            y = StepFunction(tp, yp, np.nan)

        Corresponds to

        .. code-block:: python

            if t < 0:
                y = np.nan
            elif 0 <= t < 5:
                y = -1
            else:
                y = 1

        Parameters
        ----------
        tp : 1D np.array
            Times at which a step change occurs [s].
        yp : 1D np.array
            Constant values for each time interval.
        y0 : float, optional
            Value to return when t < tp[0]. In addition to standard float
            values, np.nan and np.inf are supported. The default is 0.
        ignore_nan : bool, optional
            Whether or not to ignore NaN inputs. For NaN inputs, the callable
            returns NaN when False (default) or yp[-1] when True.

        Raises
        ------
        ValueError
            tp and yp must both be 1D.
        ValueError
            tp and yp must be same size.
        ValueError
            tp must be strictly increasing.

        Examples
        --------
        >>> tp = np.array([0, 1, 5])
        >>> yp = np.array([-1, 0, 1])
        >>> func = StepFunction(tp, yp, np.nan)
        >>> print(func(np.array([-10, 0.5, 4, 10])))
        [nan  -1.  0.  1.]

        """
        if tp.ndim != 1 or yp.ndim != 1:
            raise ValueError("tp and yp must both be 1D.")

        if tp.size != yp.size:
            raise ValueError("tp and yp must be same size.")

        if any(np.diff(tp) <= 0.):
            raise ValueError("tp must be strictly increasing.")

        self._tp = tp
        self._yp = np.concat(([y0], yp, [yp[-1]]))

        def func(t):

            t = np.asarray(t)
            if t.size == 1:
                t = np.atleast_1d(t)

            idx = np.searchsorted(tp, t, side='right')
            idx = np.clip(idx, 0, tp.size)

            y = self._yp[idx]

            if not ignore_nan:
                y[np.isnan(t)] = np.nan

            if y.size == 1:
                return y.item()
            else:
                return y

        self._func = func

    def __repr__(self) -> str:  # pragma: no cover
        return f"StepFunction(num_steps={self._tp.size})"

    def __call__(self, t: np.ndarray) -> np.ndarray:
        return self._func(t)


class RampedSteps:
    """Step function with ramps."""

    __slots__ = ('_tp', '_yp', '_func', '_t_ramp',)

    def __init__(self, tp: np.ndarray, yp: np.ndarray, t_ramp: float,
                 y0: float = 0.) -> None:
        """
        A class similar to StepFunction, with the same tp, yp, and y0, but
        step transitions include ramps with duration t_ramp. Generally, this
        profile will be more stable compared to a StepFunction profile.

        Parameters
        ----------
        tp : 1D np.array
            Times at which a step change occurs [seconds].
        yp : 1D np.array
            Constant values for each time interval.
        t_ramp : float
            Ramping time between step transitions [seconds].
        y0 : float
            Value to return when t < tp[0]. In addition to standard float
            values, np.nan and np.inf are supported. The default is 0.

        Raises
        ------
        ValueError
            tp and yp must both be 1D.
        ValueError
            tp and yp must be same size.
        ValueError
            t_ramp must be strictly positive.
        ValueError
            tp must be strictly increasing.

        See Also
        --------
        StepFunction :
            Uses hard discontinuous steps rather than ramped steps. Generally
            non-ideal for simulations, but may be useful elsewhere.

        """
        if tp.ndim != 1 or yp.ndim != 1:
            raise ValueError("tp and yp must both be 1D.")

        if tp.size != yp.size:
            raise ValueError("tp and yp must be same size.")

        if t_ramp <= 0.:
            raise ValueError("t_ramp must be strictly positive.")

        if any(np.diff(tp) <= 0.):
            raise ValueError("tp must be strictly increasing.")

        tp = np.concat((tp, tp + t_ramp))
        yp = np.concat(([y0], yp[:-1], yp))

        argsort = np.argsort(tp)

        self._tp = tp[argsort]
        self._yp = yp[argsort]
        self._t_ramp = t_ramp

        self._func = lambda t: np.interp(t, self._tp, self._yp)

    def __repr__(self) -> str:  # pragma: no cover

        num_steps = self._tp.size
        t_ramp = self._t_ramp

        return f"RampedSteps(num_steps={num_steps}, t_ramp={t_ramp:.2e})"

    def __call__(self, t: float) -> float:
        return self._func(t)
