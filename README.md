<!-- <img alt='Logo' style='width: 75%; min-width: 250px; max-width: 500px;' 
 src='https://github.com/NatLabRockies/thevenin/blob/main/images/dark.png?raw=true#gh-dark-mode-only'/>
<img alt='Logo' style='width: 75%; min-width: 250px; max-width: 500px;' 
 src='https://github.com/NatLabRockies/thevenin/blob/main/images/light.png?raw=true#gh-light-mode-only'/> -->

 # thevenin

[![ci](https://github.com/NatLabRockies/thevenin/actions/workflows/ci.yml/badge.svg)](https://github.com/NatLabRockies/thevenin/actions/workflows/ci.yml) &nbsp;
![coverage](https://github.com/NatLabRockies/thevenin/blob/main/images/coverage.svg?raw=true) &nbsp;
[![license](https://img.shields.io/badge/license-BSD--3-blue.svg)](https://github.com/NatLabRockies/thevenin/blob/main/LICENSE) &nbsp;
[![downloads](https://static.pepy.tech/personalized-badge/thevenin?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/thevenin) &nbsp;
[![pypi](https://img.shields.io/pypi/v/thevenin)](https://pypi.org/project/thevenin)

## Summary
This package is a wrapper for the well-known Thevenin equivalent circuit model. The model is comprised of a single series resistor followed by any number of parallel RC pairs. Figure 1 below illustrates a circuit with 2 RC pairs; however, the model can be run with as few as zero, and as many as $N$.

<p align="center">
  <img alt="2RC Thevenin circuit." style="width: 75%; min-width: 250px; max-width: 500px;" 
   src="https://github.com/NatLabRockies/thevenin/blob/main/images/example_circuit.png?raw=true"/>
  </br>
  Figure 1: 2RC Thevenin circuit.
</p>

This system is governed by the evolution of the state of charge (SOC, -), hysteresis ($h$, V), RC overpotentials ($V_j$, V), cell voltage ($V_{\rm cell}$, V), and temperature ($T_{\rm cell}$, K). SOC and $V_j$ evolve in time as

$$\frac{d\rm SOC}{dt} = \frac{-I \eta_{\rm ce}}{3600 Q_{\rm max}},$$
$$\frac{dV_j}{dt} = -\frac{V_j}{R_jC_j} + \frac{I}{C_j},$$

where $I$ is the load current (A), $Q_{\rm max}$ is the maximum nominal cell capacity (Ah), and $R_j$ and $C_j$ are the resistance (Ohm) and capacitance (F) of each RC pair $j$. $\eta_{\rm ce}$ is the cell's Coulombic efficiency, which is always equal to unity during discharge. Note that the sign convention for $I$ is chosen such that positive $I$ discharges the battery (reduces SOC) and negative $I$ charges the battery (increases SOC). This convention is consistent with common physics-based models, e.g., the single particle model or pseudo-2D model. While not explicitly included in the equations above, $R_j$ and $C_j$ are functions of SOC and $T_{\rm cell}$.

The hysteresis only includes a dynamic component and neglects any instantaneous effects when switching between charging and discharging directions. The hysteresis dynamics are captured by 

$$\frac{dh}{dt} = \bigg| \frac{\eta_{\rm ce} I \gamma}{3600 Q_{\rm max}} \bigg| \times (-{\rm sign}(I)M({\rm SOC}) - h),$$

The solution to this expression causes $h$ to exponentially decay toward $-{\rm sign}(I)M({\rm SOC})$ at a rate determined by the leading coefficient. The approach rate can be controlled with the unitless parameter $\gamma$. The magnitude of hysteresis $M$ can be defined as a function of SOC for maximum flexibility. The constant or expression used for $M$ should always be positive. The model internally evaluates ${\rm sign}(I)$ to force $h$ to go toward positive and negative $M$ during charge and discharge events, respectively. When calibrating a model against a cell chemistry that has negligible hysteresis, you can set both $\gamma$ and $M$ to zero.

The thermal submodel assumes uniform temperature within the cell. The temperature increases while the cell is active, according to

$$mC_p\frac{dT_{\rm cell}}{dt} = Q_{\rm gen} + Q_{\rm conv},$$

where $m$ is mass (kg), $C_p$ is specific heat capacity (J/kg/K), $Q_{\rm gen}$ is the heat generation (W), and $Q_{\rm conv}$ is the convective heat loss (W). Heat generation and convection are defined by

$$Q_{\rm gen} = I \times (V_{\rm OCV}({\rm SOC}) + h - V_{\rm cell}),$$
$$Q_{\rm conv} = h_TA(T_{\infty} - T_{\rm cell}),$$

where $h_T$ is the convecitive heat transfer coefficient (W/m<sup>2</sup>/K), $A$ is heat loss area (m<sup>2</sup>), and $T_{\infty}$ is the air/room temperature (K). $V_{\rm OCV}$ is the open circuit voltage (V) and is a function of SOC.

The overall cell voltage is

$$V_{\rm cell} = V_{\rm OCV}({\rm SOC}) + h - \sum_j V_j - IR_0,$$

where $R_0$ is the lone series resistance (Ohm), as shown in Figure 1. Just like the other resistive elements, $R_0$ is a function of SOC and $T_{\rm cell}$.

## Installation
`thevenin` is installable via either pip or conda. To install from [PyPI](https://pypi.org/project/thevenin) use the following command.

```
pip install thevenin
```

If you prefer using the `conda` package manager, you can install `thevenin` from the `conda-forge` channel using the command below.

```
conda install -c conda-forge thevenin
```

If you run into issues with installation due to the [scikit-sundae](https://github.com/NatLabRockies/scikit-sundae) dependency, please submit an issue [here](https://github.com/NatLabRockies/scikit-sundae/issues). We also manage this solver package, but distribute it separately since it is not developed in pure Python.

For those interested in setting up a developer and/or editable version of this software, please see the directions available in the "Development" section of our [documentation](https://thevenin.readthedocs.io/latest/development).

## Get Started
The API is organized around three main classes that allow you to construct the model, define an experiment, and interact with the solution. A basic example for a constant-current discharge is given below. To learn more about the model and see more detailed examples, check out the [documentation](https://thevenin.readthedocs.io/) on Read the Docs. Note that there are two interfaces to the model: `Simulation` and `Prediction`. These are optimized for full timeseries simulations and step-by-step state predictions, respectively.

```python
import thevenin as thev

sim = thev.Simulation()

expr = thev.Experiment()
expr.add_step('current_A', 75., (3600., 1.), limits=('voltage_V', 3.))

soln = sim.run(expr)
soln.plot('time_h', 'voltage_V')
```

**Notes:**
* If you are new to Python, check out [Spyder IDE](https://www.spyder-ide.org/). Spyder is a powerful interactive development environment (IDE) that can make programming in Python more approachable to new users.
* Another friendly option for getting started in Python is to use [Jupyter Notebooks](https://jupyter.org/). We write our examples in Jupyter Notebooks since they support both markdown blocks for explanations and executable code blocks.
* Python, Spyder, and Jupyter Notebooks can be setup using [Anaconda](https://www.anaconda.com/download/success). Anaconda provides a convenient way for new users to get started with Python due to its friendly graphical installer and environment manager.

## Citing this Work
This work was authored by researchers at the National Laboratory of the Rockies (NLR). If you use this package in your work, please include the following citation:

> Randall, Corey R. "thevenin: Equivalent circuit models in Python [SWR-24-132]." Computer software, Nov. 2024. url: [github.com/NatLabRockies/thevenin](https://github.com/NatLabRockies/thevenin). doi: [10.11578/dc.20241125.2](https://doi.org/10.11578/dc.20241125.2).

For convenience, we also provide the following for your BibTex:

```
@misc{randall2024thevenin,
  author = {Randall, Corey R.},
  title = {{thevenin: Equivalent circuit models in Python [SWR-24-132]}},
  url = {github.com/NatLabRockies/thevenin},
  month = {Nov.},
  year = {2024},
  doi = {10.11578/dc.20241125.2},
}
```

## Acknowledgements
The motivation and funding for this project came from the Rapid Operational Validation Initiative (ROVI) sponsored by the Office of Electricity. The focus of ROVI is "to greatly reduce time required for emerging energy storage technologies to go from lab to market by developing new tools that will accelerate the testing and validation process needed to ensure commercial success." If interested, you can read more about ROVI [here](https://www.energy.gov/oe/rapid-operational-validation-initiative-rovi).

## Contributing
If you'd like to contribute to this package, please look through the existing [issues](https://github.com/NatLabRockies/thevenin/issues). If the bug you've caught or the feature you'd like to add isn't already being worked on, please submit a new issue before getting started. You should also read through the [developer guidelines](https://thevenin.readthedocs.io/latest/development).

## Disclaimer
This work was authored by the National Laboratory of the Rockies (NLR), operated by Alliance for Energy Innovation, LLC, for the U.S. Department of Energy (DOE). The views expressed in the repository do not necessarily represent the views of the DOE or the U.S. Government.
