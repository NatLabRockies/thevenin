import warnings

import pytest
import thevenin as thev

import numpy as np
import numpy.testing as npt


def test_prediction_steps_against_simulation():

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)

        pred = thev.Prediction()
        pred.gamma = 50.0
        pred.M_hyst = lambda soc: 0.07
        pred.isothermal = False
        pred.pre()

        sim = thev.Simulation()
        sim.gamma = 50.0
        sim.M_hyst = lambda soc: 0.07
        sim.isothermal = False
        sim.pre()

    # 1C simulation discharge to compare against
    expr = thev.Experiment()
    expr.add_step('current_C', 1.0, (3600.0, 1.0))

    soln = sim.run(expr)
    assert all(soln.success)

    # step-by-step prediction comparison
    state = thev.TransientState(
        soc=soln.vars['soc'][0],
        T_cell=soln.vars['temperature_K'][0],
        hyst=soln.vars['hysteresis_V'][0],
        eta_j=np.zeros(sim.num_RC_pairs),
    )

    time_s = soln.t
    current_A = sim.capacity * np.ones(time_s.size)

    pred_V = np.empty(time_s.size)
    pred_T = np.empty(time_s.size)
    pred_h = np.empty(time_s.size)

    pred_V[0] = soln.vars['voltage_V'][0]
    pred_T[0] = soln.vars['temperature_K'][0]
    pred_h[0] = soln.vars['hysteresis_V'][0]

    pred_etaj = np.empty((time_s.size, sim.num_RC_pairs))
    for j in range(sim.num_RC_pairs):
        pred_etaj[0][j] = soln.vars[f"eta{j + 1}_V"][0]

    for i in range(3600):
        state = pred.take_step(state, current_A[i], 1.0)

        pred_V[i + 1] = state.voltage
        pred_T[i + 1] = state.T_cell
        pred_h[i + 1] = state.hyst

        for j in range(sim.num_RC_pairs):
            pred_etaj[i + 1][j] = state.eta_j[j]

    npt.assert_allclose(pred_V, soln.vars['voltage_V'], rtol=1e-3)
    npt.assert_allclose(pred_T, soln.vars['temperature_K'], rtol=1e-3)

    npt.assert_allclose(
        pred_h,
        soln.vars['hysteresis_V'],
        rtol=1e-3,
        atol=1e-3,
    )

    for j in range(sim.num_RC_pairs):
        npt.assert_allclose(
            pred_etaj[:, j],
            soln.vars[f"eta{j + 1}_V"],
            rtol=1e-3,
            atol=1e-5,
        )


def test_0_RC_pair_pred():

    params = {
        'num_RC_pairs': 0,
        'soc0': 1.0,
        'capacity': 1.0,
        'ce': 1.0,
        'gamma': 0.0,
        'mass': 1.0,
        'isothermal': True,
        'Cp': 1.0,
        'T_inf': 1.0,
        'h_therm': 1.0,
        'A_therm': 1.0,
        'ocv': lambda soc: 3.0 + (4.3 - 3.0) * soc,
        'M_hyst': lambda soc: 0.0,
        'R0': lambda soc, T_cell: 1e-3,
    }

    pred = thev.Prediction(params)
    state = thev.TransientState(soc=1.0, T_cell=300, hyst=0, eta_j=None)

    new_state = pred.take_step(state, 1.0, 3600.0)
    npt.assert_almost_equal(new_state.soc, 0.0)
    npt.assert_almost_equal(new_state.voltage, 3.0, decimal=2)


def test_dynamic_pred_step():

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        pred = thev.Prediction()

    eta_j = np.zeros(pred.num_RC_pairs)
    state = thev.TransientState(soc=1.0, T_cell=300, hyst=0, eta_j=eta_j)

    soc_0 = state.soc
    voltage_0 = pred.ocv(soc_0)

    new_state = pred.take_step(state, lambda t: 0.0, 300.0)
    npt.assert_almost_equal(new_state.soc, soc_0)
    npt.assert_almost_equal(new_state.voltage, voltage_0)


def test_incompatible_state():

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        pred = thev.Prediction()

    state = thev.TransientState(soc=1.0, T_cell=300, hyst=0, eta_j=None)

    assert pred.num_RC_pairs != state.num_RC_pairs

    with pytest.raises(ValueError):
        _ = pred.take_step(state, 0.0, 1.0)


def test_options_persist_through_pre():

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        pred = thev.Prediction()

    pred.set_options(rtol=1e-9)
    pred.pre()

    assert pred._options == {'rtol': 1e-9}


def test_to_simulation():

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)

        pred = thev.Prediction()
        sim = pred.to_simulation()

    assert pred._get_params_dict == sim._get_params_dict
