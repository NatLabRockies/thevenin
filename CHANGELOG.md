# thevenin Changelog

## [Unreleased](https://github.com/NatLabRockies/thevenin)

### New Features
- New functions to list, load, print, and download `.yaml` templates ([#26](https://github.com/NatLabRockies/thevenin/pull/26))
- Drop support for Python 3.9 and add support for 3.14 in tests/release ([#23](https://github.com/NatLabRockies/thevenin/pull/23))
- Add version warning banner to docs for dev and older releases ([#22](https://github.com/NatLabRockies/thevenin/pull/22))
- Add `to_simulation` and `to_prediction` methods to switch between interfaces ([#20](https://github.com/NatLabRockies/thevenin/pull/20))
- Allow `TransientState` as an input option to `sim.pre()` ([#14](https://github.com/NatLabRockies/thevenin/pull/14))

### Optimizations
- Change `tspan` constructor in experiments to allow floats, but not `(tmax, Nt)` ([#29](https://github.com/NatLabRockies/thevenin/pull/29))

### Bug Fixes
- Update patching policy for releases, fix warnings in tests ([#25](https://github.com/NatLabRockies/thevenin/pull/25))
- Fix links to Read the Docs `Development` page in `README` file ([#21](https://github.com/NatLabRockies/thevenin/pull/21))
- Use `for` loops in `Solution` post-processing if arrays are incompatible ([#18](https://github.com/NatLabRockies/thevenin/pull/18))

### Breaking Changes
- There is no longer a `linspace` option from `tspan: tuple[float, int]` construction ([#29](https://github.com/NatLabRockies/thevenin/pull/29))
- `initial_state` was renamed to `state0` in `sim.pre()` ([#14](https://github.com/NatLabRockies/thevenin/pull/14))

### Chores
- Swith linter over to `ruff`, enable `codecov` workflow, update README badges ([#31](https://github.com/NatLabRockies/thevenin/pull/31))
- Make GitHub hyperlinks reference new org name `NREL` -> `NatLabRockies` ([#30](https://github.com/NatLabRockies/thevenin/pull/30))
- Allow single backticks for sphinx inline code (`default_role = 'literal'`) ([#28](https://github.com/NatLabRockies/thevenin/pull/28))
- Rebrand NREL to NLR, and include name change for Alliance as well ([#27](https://github.com/NatLabRockies/thevenin/pull/27))

## [v0.2.0](https://github.com/NatLabRockies/thevenin/tree/v0.2.0)

### New Features
- Allow the `CycleSolution` to append more solutions after it has been initialized ([#9](https://github.com/NatLabRockies/thevenin/pull/9))
- New `Prediction` and `TransientState` classes for an improved interface to Kalman filters ([#8](https://github.com/NatLabRockies/thevenin/pull/8))
- Added hysteresis (`hsyt`) to the model, controlled with `gamma` and `M_hyst` parameters ([#7](https://github.com/NatLabRockies/thevenin/pull/7))

### Optimizations
- Make `num_RC_pairs` read-only so now `pre` only needs to be called to reset the state ([#13](https://github.com/NatLabRockies/thevenin/pull/13))
- Use `np.testing` where possible in tests for more informative fail statements ([#10](https://github.com/NatLabRockies/thevenin/pull/10))
- Pre-initialize `CycleSolution` arrays rather than appending lists, much faster ([#7](https://github.com/NatLabRockies/thevenin/pull/7))
- Add `ExitHandler` for single `plt.show` registrations, replaces `show_plot` option in `Solutions` ([#7](https://github.com/NatLabRockies/thevenin/pull/7))

### Bug Fixes
- Change to using `_T_ref` to scale the temperature equation since `T_inf` can be modified ([#12](https://github.com/NatLabRockies/thevenin/pull/12))
- Hyseteresis voltage was missing in `Qgen` heat transfer terms, now incorporated ([#11](https://github.com/NatLabRockies/thevenin/pull/11))

### Breaking Changes
- New hysteresis option requires updating old `params` inputs to include `gamma` and `M_hyst` ([#7](https://github.com/NatLabRockies/thevenin/pull/7))

## [v0.1.0](https://github.com/NatLabRockies/thevenin/tree/v0.1.0)
This is the first official release of `thevenin`. Main features/capabilities are listed below.

### Features
- Support for any number of RC pairs
- Run constant or dynamic loads with current, voltage, or power control
- Parameters have temperature and state of charge dependence
- Experiment limits to trigger switching between steps
- Multi-limit support (end at voltage, time, etc. - whichever occurs first)

### Notes
- Implemented `pytest` with full package coverage
- Source/binary distributions available on [PyPI](https://pypi.org/project/thevenin)
- Documentation available on [Read the Docs](https://thevenin.readthedocs.io/)

