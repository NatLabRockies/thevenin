import pytest
import thevenin as thev

import numpy as np
import numpy.testing as npt


@pytest.fixture(scope='function')
def expr():
    return thev.Experiment()


def test_initialization(expr):

    assert expr._steps == []
    assert expr._kwargs == []
    assert expr._options == {}

    assert expr.steps == []
    assert expr.num_steps == 0


def test_tspan_construction(expr):

    # using float
    expr.add_step('current_A', 0, 10)

    step = expr._steps[-1]
    npt.assert_allclose(step['tspan'], np.array([0.0, 10.0], dtype=float))

    # using arange - evenly divisible
    expr.add_step('current_A', 0, (10, 2))

    step = expr._steps[-1]
    npt.assert_allclose(
        step['tspan'], np.array([0.0, 2.0, 4.0, 6.0, 8.0, 10.0])
    )

    # using arange - not evenly divisible
    expr.add_step('current_A', 0, (10, 3))

    step = expr._steps[-1]
    npt.assert_allclose(step['tspan'], np.array([0.0, 3.0, 6.0, 9.0, 10.0]))

    # custom tspan array
    tspan = np.hstack([0.0, np.logspace(-3, 3, 10)])
    expr.add_step('current_A', 0.0, tspan)

    step = expr._steps[-1]
    npt.assert_allclose(step['tspan'], tspan)


def test_add_step(expr):

    # wrong mode
    with pytest.raises(ValueError):
        expr.add_step('voltage_mV', 0.0, (3600.0, 1.0))

    # wrong tspan length
    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, (0.0, 3600.0, 150))

    # wrong tspan type
    with pytest.raises(TypeError):
        expr.add_step('current_A', 0.0, (3600.0, '1'))

    # dt >= tmax in tspan
    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, (100.0, 100.0))

    # non-positive dt in tspan
    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, (100.0, -1.0))

    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, (100.0, 0.0))

    # wrong overall tyspan type
    with pytest.raises(TypeError):
        expr.add_step('current_A', 0.0, '3600.')

    # bad tspan arrays (doesn't start at zero, not 1D, non-monotonic, too short)
    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, np.array([1.0, 2.0, 3.0]))

    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, np.array([[0.0, 2.0, 3.0]]))

    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, np.array([0.0, 2.0, 1.0]))

    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, np.array([0.0]))

    # bad limits name
    with pytest.raises(ValueError):
        expr.add_step('current_A', 0.0, (3600.0, 1.0), limits=('fake', 3.0))

    # bad limits length
    with pytest.raises(ValueError):
        expr.add_step(
            'current_A', 0.0, (3600.0, 1.0), limits=('soc', 0.0, 'soc')
        )

    # bad limits value type
    with pytest.raises(TypeError):
        expr.add_step(
            'current_A', 0.0, (3600.0, 1.0), limits=('voltage_V', '3')
        )

    # test current and float
    expr.add_step('current_A', 1.0, 3600.0)
    step = expr.steps[0]

    assert expr.num_steps == 1
    npt.assert_allclose(step['tspan'], np.array([0.0, 3600.0], dtype=float))

    # test voltage and arange construction
    expr.add_step('voltage_V', 4.0, (3600.0, 1.0))
    step = expr.steps[1]

    assert expr.num_steps == 2
    npt.assert_allclose(step['tspan'], np.arange(0.0, 3601.0, 1.0, dtype=float))

    # test power construction
    expr.add_step('power_W', 1.0, (3600.0, 1.0))

    assert expr.num_steps == 3

    # test limit keyword
    expr.add_step('current_A', 1.0, (3600.0, 1.0), limits=('voltage_V', 3.0))

    assert expr.steps[-1]['limits'] == ('voltage_V', 3.0)

    # numpy and int limit values are valid
    limits = ('voltage_V', np.float32(3.0), 'time_s', np.int64(10), 'soc', 0)
    expr.add_step('current_A', 1.0, (3600.0, 1.0), limits=limits)

    assert expr.steps[-1]['limits'] == limits

    # test dynamic load
    expr.add_step('current_A', lambda t: 1.0, (3600.0, 1.0))
    step = expr.steps[-1]

    assert callable(step['value'])


def test_print_steps(expr, capsys):

    # no output when empty
    expr.print_steps()
    assert capsys.readouterr().out == ''

    # also works with step(s)
    expr.add_step('voltage_V', 1.0, (3600.0, 1.0))
    expr.print_steps()

    captured = capsys.readouterr().out
    assert 'Step 0' in captured
    assert 'voltage' in captured
