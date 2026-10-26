import pytest
import numpy as np


@pytest.fixture(scope='session')
def dict_params():

    coeffs = np.array([84.6, -348.6, 592.3, -534.3, 275.0, -80.3, 12.8, 2.8])

    def factory(num_RC_pairs: int = 0) -> dict:

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

    return factory
