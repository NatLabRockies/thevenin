import atexit
import warnings

import numpy as np
import numpy.testing as npt

import pytest
import thevenin as thev
import matplotlib.pyplot as plt


def dict_params(num_RC_pairs: int = 0) -> dict:

    coeffs = np.array([84.6, -348.6, 592.3, -534.3, 275.0, -80.3, 12.8, 2.8])

    params = {
        'num_RC_pairs': num_RC_pairs,
        'soc0': 0.5,
        'capacity': 1.0,
        'ce': 1.0,
        'gamma': 0.0,
        'mass': 0.5,
        'isothermal': False,
        'Cp': 1150.0,
        'T_inf': 300.0,
        'h_therm': 12.0,
        'A_therm': 1.0,
        'ocv': lambda soc: np.polyval(coeffs, soc),
        'M_hyst': lambda soc: 0.0,
        'R0': lambda soc, T_cell: 0.05 + 0.05 * soc - T_cell / 1e4,
    }

    for j in range(1, num_RC_pairs + 1):
        params['R' + str(j)] = lambda soc, T: 0.01 + 0.01 * soc - T / 3e4
        params['C' + str(j)] = lambda soc, T: 10.0 + 10.0 * soc - T / 3e1

    return params


@pytest.fixture(scope='function')  # cannot be module b/c appends
def soln():

    warnings.filterwarnings('ignore')

    sim = thev.Simulation()

    expr = thev.Experiment()
    expr.add_step(
        'current_C',
        1.0,
        (3600.0, 1.0),
        limits=('voltage_V', 3.0, 'time_s', 7200.0),
    )
    expr.add_step('current_A', 0.0, (300.0, 1.0))
    expr.add_step('current_C', -1.0, (3600.0, 1.0), limits=('voltage_V', 4.3))
    expr.add_step('current_A', 0.0, (300.0, 1.0))

    soln = sim.run(expr)

    return soln


@pytest.fixture(scope='function')
def rest():

    warnings.filterwarnings('ignore')

    sim = thev.Simulation()

    rest = thev.Experiment()
    rest.add_step('current_A', 0.0, (300.0, 1.0))

    soln = sim.run(rest)

    return soln


def test_step_and_cycle_solutions(soln):

    # solvetime works
    step_soln = soln.get_steps(0)
    assert step_soln.solvetime

    # bad plot
    with pytest.raises(KeyError):
        step_soln.plot('fake', 'plot')

    # plots w/ and w/o units
    with plt.ioff():
        step_soln.plot('soc', 'soc')
        step_soln.plot('time_h', 'voltage_V')
        plt.close('all')

    # solvetime works and times stacked correctly
    cycle_soln = soln.get_steps((0, 1))
    assert cycle_soln.solvetime
    assert all(np.diff(cycle_soln.t) >= 0.0)

    # bad plot
    with pytest.raises(KeyError):
        cycle_soln.plot('fake', 'plot')

    # plots w/ and w/o units
    with plt.ioff():
        cycle_soln.plot('soc', 'soc')
        cycle_soln.plot('time_h', 'voltage_V')
        plt.close('all')


def test_cycle_from_single_step(soln):

    step0 = soln.get_steps(0)
    assert isinstance(step0, thev.StepSolution)

    cycle = thev.CycleSolution(step0)
    assert isinstance(cycle, thev.CycleSolution)


def test_get_steps(soln):

    # numpy integers are valid
    step = soln.get_steps(np.int64(1))
    assert isinstance(step, thev.StepSolution)

    # bad idx type
    with pytest.raises(TypeError):
        _ = soln.get_steps('0')

    # bad idx tuple length
    with pytest.raises(TypeError):
        _ = soln.get_steps((0, 1, 2))


def test_i_events(soln):

    # one entry for each step that hit a limit
    assert len(soln.i_events) == 2

    # correct number of events for each step that hit a limit
    assert len(soln.i_events[0]) == 2  # time or voltage
    assert len(soln.i_events[1]) == 1  # only voltage

    # correctly appends an extra event when adding a step solution with events
    soln.append_soln(soln.get_steps(0))
    assert len(soln.i_events) == 3

    # correctly extends events when adding cycle solution with events
    soln.append_soln(soln)
    assert len(soln.i_events) == 6


def test_exit_handler():
    from thevenin._solutions import ExitHandler

    def func():
        pass

    ExitHandler.register_atexit(func)
    ExitHandler.register_atexit(func)

    assert ExitHandler._registered.count(func) == 1

    atexit.unregister(func)
    ExitHandler._registered.remove(func)


def test_append_errors(soln):

    # append wrong size solution (different num_RC_pairs)
    sim0 = thev.Simulation(dict_params(0))
    sim1 = thev.Simulation(dict_params(1))

    expr = thev.Experiment()
    expr.add_step('current_C', 1.0, (3600.0, 1.0), limits=('voltage_V', 3.0))

    soln0 = sim0.run(expr)
    soln1 = sim1.run(expr)
    with pytest.raises(ValueError):
        soln0.append_soln(soln1)

    # only works with StepSolution and CycleSolution
    sim = soln._sim
    with pytest.raises(TypeError):
        soln.append_soln(sim)


def test_append_step_soln(soln):

    t_orig = soln.vars['time_s']
    V_orig = soln.vars['voltage_V']

    step0 = soln.get_steps(0)

    soln.append_soln(step0, t_shift=0.0)
    assert len(soln.success) == 5

    t_new_times = t_orig[-1] + step0.vars['time_s']
    t_append = np.concatenate([t_orig, t_new_times])
    npt.assert_allclose(soln.vars['time_s'], t_append)

    V_append = np.concatenate([V_orig, step0.vars['voltage_V']])
    npt.assert_allclose(soln.vars['voltage_V'], V_append)


def test_append_cycle_soln(soln):

    t_orig = soln.vars['time_s']
    V_orig = soln.vars['voltage_V']

    soln.append_soln(soln, t_shift=0.0)
    assert len(soln.success) == 8

    t_new_times = t_orig[-1] + t_orig
    t_append = np.concatenate([t_orig, t_new_times])
    npt.assert_allclose(soln.vars['time_s'], t_append)

    V_append = np.concatenate([V_orig, V_orig])
    npt.assert_allclose(soln.vars['voltage_V'], V_append)


def test_append_w_events(rest, soln):

    rest.append_soln(soln)
    assert len(rest.t_events) == 2


def test_np_incompatible_funcs():

    def ocv(soc):
        if isinstance(soc, np.ndarray):
            raise TypeError("ocv cannot accept numpy arrays.")
        return 3.8

    def R0(soc, T_cell):
        if isinstance(soc, np.ndarray):
            raise TypeError("R0 cannot accept numpy arrays.")
        elif isinstance(T_cell, np.ndarray):
            raise TypeError("R0 cannot accept numpy arrays.")
        return 3.8

    expr = thev.Experiment()
    expr.add_step('current_A', 0.0, (100.0, 1.0))

    # with ocv that cannot handle numpy arrays
    params = dict_params(0)
    params['ocv'] = ocv

    model = thev.Simulation(params)
    soln = model.run(expr)

    assert all(soln.success)
    npt.assert_allclose(soln.vars['voltage_V'], 3.8)

    # with R0 that cannot handle numpy arrays
    params = dict_params(0)
    params['R0'] = R0

    model = thev.Simulation(params)
    soln = model.run(expr)

    assert all(soln.success)
    npt.assert_allclose(soln.vars['eta0_V'], 0.0)

    # with ocv that raises ValueError for arrays, e.g., if statements
    params = dict_params(0)
    params['ocv'] = lambda soc: 3.8 if soc < 2.0 else 4.0

    model = thev.Simulation(params)
    soln = model.run(expr)

    assert all(soln.success)
    npt.assert_allclose(soln.vars['voltage_V'], 3.8)
