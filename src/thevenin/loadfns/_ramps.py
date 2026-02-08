from __future__ import annotations

import numpy as np


class Ramp:
    """Linearly ramping load."""

    __slots__ = ('_m', '_b',)

    def __init__(self, m: float, b: float = 0.) -> None:
        """
        A load profile that continuously ramps with slope m.

        Parameters
        ----------
        m : float
            Slope [units/s].
        b : float, optional
            Y-intercept [units]. The default is 0.

        """
        self._m = m
        self._b = b

    def __repr__(self) -> str:  # pragma: no cover
        return f"Ramp(m={self._m:.2e}, b={self._b:.2e})"

    def __call__(self, t: float) -> float:
        return self._m*t + self._b


class Ramp2Constant:
    """Ramp to a constant load."""

    __slots__ = ('_m', '_b', '_step', '_sharpness',)

    def __init__(self, m: float, step: float, b: float = 0.,
                 sharpness: float = 100.) -> None:
        """
        A load profile that ramps with slope m unil the constant step value
        is reached, after which, the load is equal to the step constant. A
        sigmoid is used to smooth the transition between the two piecewise
        functions. Use a large 'sharpness' to reduce smoothing effects.

        Parameters
        ----------
        m : float
            Slope [units/s].
        step : float
            Constant step value [units].
        b : float, optional
            Y-intercept [units]. The default is 0.
        sharpness : float, optional
            How sharp to make the transition between the ramp and step. Low
            values will smooth the transition more. The default is 100.

        Raises
        ------
        ValueError
            m = 0. and m = inf are invalid slopes.
        ValueError
            Cannot reach step with m > 0. and b >= step.
        ValueError
            Cannot reach step with m < 0. and b <= step.
        ValueError
            'sharpness' must be strictly positive.

        """
        if m == 0. or abs(m) == np.inf:
            raise ValueError("m = 0. and m = inf are invalid slopes.")
        elif m > 0. and b >= step:
            raise ValueError("Cannot reach step with m > 0. and b >= step.")
        elif m < 0. and b <= step:
            raise ValueError("Cannot reach step with m < 0. and b <= step.")

        if sharpness <= 0:
            raise ValueError("'sharpness' must be strictly positive.")

        self._m = m
        self._b = b
        self._step = step
        self._sharpness = np.sign(m)*sharpness

    def __repr__(self) -> str:  # pragma: no cover

        data = {'m': self._m, 'b': self._b, 'step': self._step}

        summary = ", ".join([f"{k}={v:.2e}" for k, v in data.items()])

        return f"Ramp2Constant({summary})"

    def __call__(self, t: float) -> float:

        linear = self._m*t + self._b

        z = self._sharpness*(linear - self._step)
        sigmoid = 1. / (1. + np.exp(-np.clip(z, -700, None)))

        return (1. - sigmoid)*linear + sigmoid*self._step
