from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from numpy import ndarray


def get_colors(size: int, data: ndarray = None, norm: ndarray = None,
               alpha: float = 1., cmap: str = 'jet'):
    """
    Sample colors from 'cmap'.

    Return a list of colors from a specified colormap. Default options will
    provide evenly spaced colors across 'cmap'. Provide 'data' and/or 'norm'
    to control the ordering, spacing, and normalization.

    Parameters
    ----------
    size : int
        Number of colors to return.
    data : array_like[float] or None, optional
        A 1D array with length 'size' that controls the spacing and sorting of
        the output. By default, spacing is equal and sorting matches 'cmap'.
    norm : array_like[float] or None, optional
        An array-like (min, max) pair that normalizes the colormap to 'data'.
        By default (0, size) if 'data=None' or min/max of 'data' otherwise.
    alpha : float, optional
        Transparency to apply over the colormap. Must be in the range [0, 1].
        The default is 1.
    cmap : str, optional
        A valid matplotlib colormap name. The default is 'jet'.

    Returns
    -------
    colors : list
        A list of (r, g, b, a) color codes.

    Raises
    ------
    ValueError
        'data' length must match 'size'.
    ValueError
        'norm' length must equal 2.

    """
    import numpy as np
    import matplotlib as mpl

    if data is None:
        data = np.arange(size)
    elif len(data) != size:
        raise ValueError(f"{len(data)=} does not match {size=}.")

    if norm is None:
        norm = (min(data), max(data))
    elif len(norm) != 2:
        raise ValueError(f"{len(norm)=} does not match 2.")

    cmap = mpl.colormaps[cmap]

    norm = mpl.colors.Normalize(vmin=norm[0], vmax=norm[1])
    sm = mpl.pyplot.cm.ScalarMappable(cmap=cmap, norm=norm)

    colors = [sm.to_rgba(x, alpha=alpha) for x in data]

    return colors
