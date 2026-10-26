import pathlib
import warnings

import pytest
import numpy as np
import thevenin as thev
import numpy.testing as npt

from scipy.integrate import cumulative_trapezoid


@pytest.fixture(scope='function')
def sim_0RC(dict_params):
    params = dict_params(0)
    return thev.Simulation(params)


@pytest.fixture(scope='function')
def sim_1RC(dict_params):
    params = dict_params(1)
    return thev.Simulation(params)


@pytest.fixture(scope='function')
def sim_2RC(dict_params):
    params = dict_params(2)
    return thev.Simulation(params)


@pytest.fixture(scope='function')
def constant_steps():
    expr = thev.Experiment()
    expr.add_step('current_A', 1.0, (3600.0, 1.0), limits=('voltage_V', 3.0))
    expr.add_step('current_C', 0.0, (600.0, 1.0))
    expr.add_step('current_A', -1.0, (3600.0, 1.0), limits=('voltage_V', 4.3))
    expr.add_step('voltage_V', 4.3, (600.0, 1.0))
    expr.add_step('power_W', 1.0, (600.0, 1.0), limits=('voltage_V', 3.0))
    expr.add_step('current_A', 0.0, 600.0)  # solver picks time steps

    return expr


@pytest.fixture(scope='function')
def dynamic_current():
    def load(t):
        return np.sin(2.0 * np.pi * t / 120.0)

    expr = thev.Experiment()
    expr.add_step('current_A', load, (600.0, 1.0))

    return expr


@pytest.fixture(scope='function')
def dynamic_voltage():
    def load(t):
        return 3.8 + 10e-3 * np.sin(2.0 * np.pi * t / 120.0)

    expr = thev.Experiment()
    expr.add_step('voltage_V', load, (600.0, 1.0))

    return expr


@pytest.fixture(scope='function')
def dynamic_power():
    def load(t):
        return np.sin(2.0 * np.pi * t / 120.0)

    expr = thev.Experiment()
    expr.add_step('power_W', load, (600.0, 1.0))

    return expr


def test_bad_initialization(dict_params):

    # wrong params type
    with pytest.raises(TypeError):
        _ = thev.Simulation(['wrong_type'])

    # invalid/excess key/value pairs
    params = dict_params()
    params['fake'] = 'parameter'
    with pytest.raises(ValueError):
        _ = thev.Simulation(params)

    # missing required key
    params = dict_params()
    _ = params.pop('soc0')
    with pytest.raises(ValueError):
        _ = thev.Simulation(params)


def test_sim_w_pathlike_input():
    from thevenin._basemodel import _yaml_reader

    resources = pathlib.Path(thev.__file__).parent.joinpath('_resources')

    sim = thev.Simulation(resources.joinpath('params.yaml'))
    params = _yaml_reader(resources.joinpath('params.yaml'))

    assert sim.num_RC_pairs == params['num_RC_pairs']


def test_local_yaml_paths_override_defaults(tmp_path, monkeypatch):
    from thevenin._basemodel import _yaml_reader

    resources = pathlib.Path(thev.__file__).parent.joinpath('_resources')

    text = resources.joinpath('params.yaml').read_text()
    text = text.replace('soc0: 1.', 'soc0: 0.25')
    assert 'soc0: 0.25' in text

    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath('params.yaml').write_text(text)

    # explicit relative paths and Path objects use the local file
    with warnings.catch_warnings():
        warnings.simplefilter('error')  # no default file warning
        params = _yaml_reader('./params.yaml')
        assert params['soc0'] == 0.25

        params = _yaml_reader(pathlib.Path('params.yaml'))
        assert params['soc0'] == 0.25

    # bare names still prefer the internal resource, with a warning
    with pytest.warns(UserWarning):
        params = _yaml_reader('params.yaml')
        assert params['soc0'] == 1.0


def test_sim_w_yaml_input(
    constant_steps, dynamic_current, dynamic_voltage, dynamic_power
):

    # using default file
    with pytest.warns(UserWarning):
        sim = thev.Simulation()

    # using default file by name
    with pytest.warns(UserWarning):
        sim = thev.Simulation('params')

    # using default file by name w/ extension
    with pytest.warns(UserWarning):
        sim = thev.Simulation('params.yaml')

    soln = sim.run(constant_steps)
    assert all(soln.success)
    assert soln.i_events is not None
    assert isinstance(soln.i_events, list)

    soln = sim.run(dynamic_current)
    assert all(soln.success)

    soln = sim.run(dynamic_voltage)
    assert all(soln.success)

    soln = sim.run(dynamic_power)
    assert all(soln.success)


def test_bad_yaml_inputs(dict_params):

    # only .yaml extensions
    with pytest.raises(ValueError):
        _ = thev.Simulation('fake.fake')

    # file doesn't exist
    with pytest.raises(FileNotFoundError):
        _ = thev.Simulation('fake')

    # missing attrs
    params = dict_params(1)
    _ = params.pop('R1')
    with pytest.raises(ValueError):
        _ = thev.Simulation(params)

    params = dict_params(1)
    _ = params.pop('C1')
    with pytest.raises(ValueError):
        _ = thev.Simulation(params)

    # extra attrs
    params = dict_params(1)
    params['R2'] = lambda soc, T_cell: 0.01 + 0.01 * soc - T_cell / 3e4
    with pytest.raises(ValueError):
        _ = thev.Simulation(params)


def test_preprocessor_raises(dict_params, dynamic_current):

    # can't change num_RC_pairs
    sim = thev.Simulation(dict_params(0))
    with pytest.raises(AttributeError):
        sim.num_RC_pairs = 1

    # missing attrs
    sim = thev.Simulation(dict_params(1))

    del sim.R1
    with pytest.raises(AttributeError):
        sim.pre()

    sim = thev.Simulation(dict_params(1))

    del sim.C1
    with pytest.raises(AttributeError):
        sim.pre()

    # extra attrs - warning
    sim = thev.Simulation(dict_params(1))
    sim.R2 = lambda soc, T_cell: 0.01 + 0.01 * soc - T_cell / 3e4
    with pytest.warns(UserWarning):
        sim.pre()

    # soln size inconsistent with sim
    sim0 = thev.Simulation(dict_params(0))
    sim1 = thev.Simulation(dict_params(1))

    soln = sim0.run(dynamic_current)
    with pytest.raises(ValueError):
        sim1.pre(state0=soln)


def test_preprocessing_state0_options(sim_2RC, constant_steps):
    sv0 = sim_2RC._sv0.copy()
    svdot0 = sim_2RC._svdot0.copy()

    soln = sim_2RC.run(constant_steps)
    npt.assert_allclose(sv0, sim_2RC._sv0)
    npt.assert_allclose(svdot0, sim_2RC._svdot0)

    # given a Solution instance
    sim_2RC.pre(state0=soln)
    npt.assert_allclose(soln.y[-1], sim_2RC._sv0)
    npt.assert_allclose(soln.yp[-1], sim_2RC._svdot0)

    # with bool values
    sim_2RC.pre(state0=False)
    npt.assert_allclose(soln.y[-1], sim_2RC._sv0)
    npt.assert_allclose(soln.yp[-1], sim_2RC._svdot0)

    sim_2RC.pre()
    npt.assert_allclose(sv0, sim_2RC._sv0)
    npt.assert_allclose(svdot0, sim_2RC._svdot0)

    # given a TransientState
    state = thev.TransientState(
        soc=0.5,
        T_cell=400.0,
        hyst=10.0,
        eta_j=None,
    )
    with pytest.raises(ValueError):  # incompatible num_RC_pairs
        sim_2RC.pre(state)

    state = thev.TransientState(
        soc=0.5,
        T_cell=400.0,
        hyst=10.0,
        eta_j=[1e-3, 1e-3],
    )

    sv0 = np.zeros(sim_2RC._ptr['size'])
    sv0[sim_2RC._ptr['soc']] = state.soc
    sv0[sim_2RC._ptr['T_cell']] = state.T_cell / sim_2RC._T_ref
    sv0[sim_2RC._ptr['hyst']] = state.hyst
    sv0[sim_2RC._ptr['eta_j']] = state.eta_j
    sv0[sim_2RC._ptr['V_cell']] = sim_2RC.ocv(state.soc)

    svdot0 = np.zeros_like(sv0)

    sim_2RC.pre(state0=state)
    npt.assert_allclose(sv0, sim_2RC._sv0)
    npt.assert_allclose(svdot0, sim_2RC._svdot0)


def test_run_step(sim_2RC, constant_steps):

    sv0 = sim_2RC._sv0.copy()
    svdot0 = sim_2RC._svdot0.copy()

    stepsoln = sim_2RC.run_step(constant_steps, 0)

    assert stepsoln.success
    assert not np.allclose(sv0, sim_2RC._sv0)
    assert not np.allclose(svdot0, sim_2RC._svdot0)

    sim_2RC.pre()

    npt.assert_allclose(sv0, sim_2RC._sv0)
    npt.assert_allclose(svdot0, sim_2RC._svdot0)


def test_time_limits_use_total_time(sim_1RC):

    expr = thev.Experiment()
    expr.add_step('current_A', 0.0, (100.0, 1.0))
    expr.add_step('current_A', 0.0, (100.0, 1.0))
    expr.add_step(
        'current_A', 0.0, (500.0, 1.0), limits=('time_s', 250.0), max_step=1.0
    )

    # stitched solutions include a small t_shift between steps
    soln = sim_1RC.run(expr, t_shift=0.0)

    step = soln.get_steps(2)
    npt.assert_allclose(step.t_events, 50.0, atol=1.0)
    npt.assert_allclose(soln.t[-1], 250.0, atol=1.0)

    # total time also resets between runs
    soln = sim_1RC.run(expr, t_shift=0.0)
    npt.assert_allclose(soln.t[-1], 250.0, atol=1.0)


def test_limits_are_exact(sim_1RC):

    expr = thev.Experiment()
    expr.add_step('current_C', 1.0, (4000.0, 10.0), limits=('voltage_V', 3.6))
    expr.add_step('current_C', -1.0, (4000.0, 10.0), limits=('soc', 0.9))

    soln = sim_1RC.run(expr)

    discharge = soln.get_steps(0)
    npt.assert_allclose(discharge.vars['voltage_V'][-1], 3.6, atol=0.01)

    charge = soln.get_steps(1)
    npt.assert_allclose(charge.vars['soc'][-1], 0.9, atol=0.01)


def test_simulation_subclass(dict_params, dynamic_current):

    class CustomSimulation(thev.Simulation):
        pass

    sim = CustomSimulation(dict_params(1))
    soln = sim.run(dynamic_current)

    assert all(soln.success)


def test_run_options(sim_0RC, constant_steps):
    sv0 = sim_0RC._sv0.copy()
    svdot0 = sim_0RC._svdot0.copy()

    soln = sim_0RC.run(constant_steps)
    npt.assert_allclose(sv0, sim_0RC._sv0)
    npt.assert_allclose(svdot0, sim_0RC._svdot0)

    soln = sim_0RC.run(constant_steps, reset_state=False)
    npt.assert_allclose(soln.y[-1], sim_0RC._sv0)
    npt.assert_allclose(soln.yp[-1], sim_0RC._svdot0)


def test_sim_w_multistep_experiment(sim_0RC, sim_1RC, sim_2RC, constant_steps):

    soln = sim_0RC.run(constant_steps)
    assert all(soln.success)
    assert any(status == 2 for status in soln.status)

    soln = sim_1RC.run(constant_steps)
    assert all(soln.success)
    assert any(status == 2 for status in soln.status)

    soln = sim_2RC.run(constant_steps)
    assert all(soln.success)
    assert any(status == 2 for status in soln.status)

    # solver-chosen time steps works
    step = soln.get_steps(-1)
    assert step.vars['time_s'].size > 2


def test_sim_w_dynamic_current(sim_0RC, sim_1RC, sim_2RC, dynamic_current):

    soln = sim_0RC.run(dynamic_current)
    assert all(soln.success)

    soln = sim_1RC.run(dynamic_current)
    assert all(soln.success)

    soln = sim_2RC.run(dynamic_current)
    assert all(soln.success)


def test_sim_w_dynamic_voltage(sim_0RC, sim_1RC, sim_2RC, dynamic_voltage):

    soln = sim_0RC.run(dynamic_voltage)
    assert all(soln.success)

    soln = sim_1RC.run(dynamic_voltage)
    assert all(soln.success)

    soln = sim_2RC.run(dynamic_voltage)
    assert all(soln.success)


def test_sim_w_dynamic_power(sim_0RC, sim_1RC, sim_2RC, dynamic_power):

    soln = sim_0RC.run(dynamic_power)
    assert all(soln.success)

    soln = sim_1RC.run(dynamic_power)
    assert all(soln.success)

    soln = sim_2RC.run(dynamic_power)
    assert all(soln.success)


def test_resting_experiment(sim_2RC):

    expr = thev.Experiment()
    expr.add_step('current_A', 0.0, (100.0, 1.0))

    soln = sim_2RC.run(expr)

    assert all(soln.success)
    npt.assert_allclose(
        soln.vars['voltage_V'],
        soln.vars['voltage_V'][0],
    )


def test_current_sign_convention(sim_2RC, constant_steps):

    soln = sim_2RC.run(constant_steps)

    discharge = soln.get_steps(0)
    assert all(np.diff(discharge.vars['voltage_V']) < 0.0)

    charge = soln.get_steps(2)
    assert all(np.diff(charge.vars['voltage_V']) > 0.0)


def test_constant_V_shift_w_constant_R0(sim_0RC, constant_steps):

    sim_0RC.R0 = lambda soc, T_cell: 1e-2
    sim_0RC.pre()

    soln = sim_0RC.run(constant_steps)

    discharge = soln.get_steps(0)
    ocv = sim_0RC.ocv(discharge.vars['soc'])
    npt.assert_allclose(
        discharge.vars['voltage_V'],
        ocv - 1e-2,
        rtol=1e-3,
    )

    charge = soln.get_steps(2)
    ocv = sim_0RC.ocv(charge.vars['soc'])
    npt.assert_allclose(
        charge.vars['voltage_V'],
        ocv + 1e-2,
        rtol=1e-3,
    )


def test_isothermal_flag(sim_2RC, constant_steps):

    # with heat on
    sim_2RC.isothermal = False
    sim_2RC.pre()

    soln = sim_2RC.run(constant_steps)
    assert soln.vars['temperature_K'].max() > sim_2RC.T_inf
    assert all(soln.vars['temperature_K'] >= sim_2RC.T_inf)

    # with heat off
    sim_2RC.isothermal = True
    sim_2RC.pre()

    soln = sim_2RC.run(constant_steps)
    npt.assert_allclose(soln.vars['temperature_K'], sim_2RC.T_inf)


@pytest.mark.filterwarnings("ignore:.*default parameter file.*:UserWarning")
def test_coulombic_efficiency():

    sim_100 = thev.Simulation()
    sim_100.soc0 = 1.0
    sim_100.ce = 1.0
    sim_100.pre()

    sim_80 = thev.Simulation()
    sim_80.soc0 = 1.0
    sim_80.ce = 0.8
    sim_80.pre()

    expr = thev.Experiment()
    expr.add_step('current_C', 0.05, (3600.0 * 30.0, 10.0), limits=('soc', 0.0))
    expr.add_step(
        'current_C', -0.05, (3600.0 * 30.0, 10.0), limits=('soc', 1.0)
    )

    # check discharge capacity / charge capacity ~ 1.0
    soln_100 = sim_100.run(expr)
    assert all(soln_100.success)

    dis = soln_100.get_steps(0)
    chg = soln_100.get_steps(1)

    cap_dis = cumulative_trapezoid(
        dis.vars['current_A'], dis.vars['time_h'], initial=0.0
    )
    cap_chg = cumulative_trapezoid(
        chg.vars['current_A'], chg.vars['time_h'], initial=0.0
    )

    assert round(abs(cap_dis).max() / abs(cap_chg).max(), 1) == 1.0

    # check discharge capacity / charge capacity ~ 0.8
    soln_80 = sim_80.run(expr)
    assert all(soln_80.success)

    dis = soln_80.get_steps(0)
    chg = soln_80.get_steps(1)

    cap_dis = cumulative_trapezoid(
        dis.vars['current_A'], dis.vars['time_h'], initial=0.0
    )
    cap_chg = cumulative_trapezoid(
        chg.vars['current_A'], chg.vars['time_h'], initial=0.0
    )

    assert round(abs(cap_dis).max() / abs(cap_chg).max(), 1) == 0.8


@pytest.mark.filterwarnings("ignore:.*default parameter file.*:UserWarning")
def test_hysteresis():

    sim_woh = thev.Simulation()  # without hysteresis
    sim_woh.soc0 = 1.0
    sim_woh.pre()

    assert sim_woh.gamma == 0.0
    assert sim_woh.M_hyst(0.0) == 0.0

    sim_wh = thev.Simulation()  # with hysteresis
    sim_wh.soc0 = 1.0
    sim_wh.gamma = 50.0
    sim_wh.M_hyst = lambda soc: 0.07
    sim_wh.pre()

    assert sim_wh.gamma == 50.0
    assert sim_wh.M_hyst(0.0) == 0.07

    discharge = thev.Experiment(max_step=10.0)
    discharge.add_step('current_C', 1.0, (3600.0, 10.0), limits=('soc', 0.5))
    discharge.add_step('current_A', 0.0, (600.0, 10.0))

    charge = thev.Experiment(max_step=10.0)
    charge.add_step('current_C', -1.0, (3600.0, 10.0), limits=('soc', 0.8))
    charge.add_step('current_A', 0.0, (600.0, 10.0))

    soln = sim_woh.run(discharge, reset_state=False)
    npt.assert_allclose(soln.vars['hysteresis_V'], 0.0, atol=1e-9)
    npt.assert_almost_equal(
        soln.vars['voltage_V'][-1],
        sim_woh.ocv(0.5),
        decimal=2,
    )

    soln = sim_woh.run(charge, reset_state=False)
    npt.assert_allclose(soln.vars['hysteresis_V'], 0.0, atol=1e-9)
    npt.assert_almost_equal(
        soln.vars['voltage_V'][-1],
        sim_woh.ocv(0.8),
        decimal=2,
    )

    soln = sim_wh.run(discharge, reset_state=False)
    npt.assert_allclose(soln.vars['hysteresis_V'][-1], -0.07, rtol=1e-4)
    npt.assert_almost_equal(
        soln.vars['voltage_V'][-1],
        sim_wh.ocv(0.5) - 0.07,
        decimal=2,
    )

    soln = sim_wh.run(charge, reset_state=False)
    npt.assert_allclose(soln.vars['hysteresis_V'][-1], 0.07, rtol=1e-4)
    npt.assert_almost_equal(
        soln.vars['voltage_V'][-1],
        sim_wh.ocv(0.8) + 0.07,
        decimal=2,
    )

    # Check current is unaffected by hysteresis
    step = soln.get_steps(0)
    npt.assert_allclose(
        step.vars['current_A'],
        -1.0 * sim_wh.capacity,
        rtol=1e-3,
    )


def test_to_prediction():

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)

        sim = thev.Simulation()
        pred = sim.to_prediction()

    assert sim._get_params_dict == pred._get_params_dict
