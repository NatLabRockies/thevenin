import warnings

import pytest
import numpy as np
import numpy.testing as npt


def test_no_basemodel_instances():
    from thevenin._basemodel import BaseModel

    with pytest.raises(TypeError):
        _ = BaseModel()


def test_calculated_current():
    from thevenin._basemodel import calculated_current

    voltage = 4.0
    ocv = 4.0
    hyst = 0.0
    R0 = 1.0

    # with 1D eta_j
    eta_j = np.zeros(3)
    assert calculated_current(voltage, ocv, hyst, eta_j, R0) == 0.0

    # with 2D eta_j
    eta_j = np.zeros((500, 3))
    npt.assert_allclose(
        calculated_current(voltage, ocv, hyst, eta_j, R0),
        np.zeros(500),
    )

    # with higher-dimension eta_j
    eta_j = np.zeros((500, 3, 3))
    with pytest.raises(ValueError):
        _ = calculated_current(voltage, ocv, hyst, eta_j, R0)


def test_calculated_voltage():
    from thevenin._basemodel import calculated_voltage

    current = 0.0
    ocv = 4.0
    hyst = 0.0
    R0 = 1.0

    # with 1D eta_j
    eta_j = np.zeros(3)
    assert calculated_voltage(current, ocv, hyst, eta_j, R0) == ocv

    # with 2D eta_j
    eta_j = np.zeros((500, 3))
    npt.assert_allclose(
        calculated_voltage(current, ocv, hyst, eta_j, R0),
        ocv * np.ones(500),
    )

    # with higher-dimension eta_j
    eta_j = np.zeros((500, 3, 3))
    with pytest.raises(ValueError):
        _ = calculated_voltage(current, ocv, hyst, eta_j, R0)


def test_mutable_warning():
    from thevenin._basemodel import short_warn

    with warnings.catch_warnings(record=True) as report:
        warnings.simplefilter('ignore')
        short_warn("This is a test warning.")

    assert len(report) == 0


def test_detected_warning():
    from thevenin._basemodel import short_warn

    with pytest.warns(UserWarning):
        short_warn("This is a test warning")


def test_custom_format():
    from thevenin._basemodel import formatwarning, short_warn

    with warnings.catch_warnings(record=True) as report:
        warnings.simplefilter('always')
        short_warn("This is a test warning.", Warning)

    args = (
        report[0].message,
        report[0].category,
        report[0].filename,
        report[0].lineno,
        report[0].line,
    )

    # ensure the same inputs, remove  any \n, \t, etc.
    custom = formatwarning(*args).strip()
    original = warnings.formatwarning(*args).strip()

    # custom format works
    assert custom == "[thevenin Warning] This is a test warning."

    # warnings from warnings.warn not impacted by custom format
    assert original != "[thevenin Warning] This is a test warning."
