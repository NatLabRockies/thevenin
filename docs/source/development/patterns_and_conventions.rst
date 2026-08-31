Patterns and Conventions
========================

File Organization
-----------------
It is preferred to have more files with fewer lines of code rather than fewer, larger files. This keeps the codebase easier to navigate and review. As a rule of thumb, classes and functions that are long should be in their own file, while shorter, related items can be grouped together. However, take care to not group unrelated classes and/or functions just because they are short. It is okay for these to still be in their own files if they are unique and cannot be categorized to fit in with other classes/functions.

To maintain ease of access for users, all user-facing functions and classes should be no more than three levels deep from the top-level of the package. This ensures that users do not need to navigate through excessive subpackages or submodules to find the tools they need. Keeping interfaces easily discoverable improves usability and reduces friction when working with the package. With this in mind, it is still okay for developers to have nested code, however, they should import user-facing functionality into the package or some subpackage that makes it more accessible.

Naming Convention
-----------------
To ensure consistency and ease of development, the following conventions are enforced:

1. File names: 
    All file names begin with a leading underscore (`_`) to prevent them from showing up in an editor's tab completion window. File names also use snake case (e.g., `_my_class.py`) and are generally short but descriptive. Typically, the name of the file should reflect the class or function it contains.

2. Class and function names: 
    Classes use `PascalCase`. Functions, methods, and variables use `snake_case`. Classes should generally be in their own file unless grouped logically with others. Use preceding `_` for hidden/internal classes, functions, variables, etc.

3. Constants: 
    Constants are defined at the top of a file and use `UPPERCASE_SNAKE_CASE`. This makes them easily identifiable and accessible for users.

Import Considerations
---------------------

Ordering
^^^^^^^^
In our codebase, import statements are organized into three distinct groups based on where the modules originate. This helps keep imports clean and maintainable. The groups, in order, are:

1. **Standard Library Imports:** These come from Python's built-in standard library.
2. **Dependency Imports:** Imports from external dependencies installed via package managers (e.g., `pip` or `conda`).
3. **Local Package Imports:** Imports that come from within our package.

Within each group, we generally list imports in ascending order of their length (shortest to longest), as shown in the example below. This helps maintain a neat and consistent style throughout the code. Note that it is not necessary to comment each grouped section, this is only done for clarity in the example.

.. code-block:: python

    # Standard Library Imports
    import os
    import sys
    import datetime

    # Dependency Imports
    import numpy as np
    import matplotlib.pyplot as plt

    # Local Package Imports
    from ._experiment import Experiment
    from thevenin.plotutils import StepFunction

Placement
^^^^^^^^^
* Common dependencies that are used across multiple functions should be imported at the top of the module.
* For heavier dependencies or rarely used ones, consider importing them only where needed (within functions/methods) to minimize unnecessary load times.
* Regardless of placement, at the top of a file of within a function/method, ordering within each group should follow the ordering listed above.

Class Considerations
--------------------
For class definitions, we follow a specific ordering convention to make it easier to navigate through the code:

1. **Magic Methods:** These special methods (e.g., `__init__`, `__repr__`, etc.) come first. They define key behaviors of the class.
2. **Special Members:** Any properties, class methods, static methods, etc. Essentially, any decorated and/or "special" methods.
3. **User-Facing Methods:** These are the public methods intended for external use. They define the class's core functionality for users.
4. **Hidden Methods:** These are internal methods (denoted with a leading underscore) that handle functionality not meant to be directly accessed by users.

In some cases, exceptions to this order may be made, particularly if moving a hidden method closer to a user-facing method improves readability. However, this should be done with discretion and only when it helps clarify the flow of the class's logic. See below for an example.

.. code-block:: python

    class MyClass:
        # Magic Methods
        def __init__(self, value: int) -> None:
            self._value = value
        
        def __repr__(self) -> str:
            return f"MyClass(value={self.value})"

        # Special Members
        @property
        def value(self) -> int:
        return self._value
        
        # User-Facing Methods
        def do_something(self) -> str:
            self._helper_function()
            return f"Value is {self.value}"
        
        # Hidden Methods
        def _helper_function(self):
            # Some internal logic
            pass

Module Considerations
---------------------
In our modules, we maintain a consistent structure to enhance readability and organization. The general order is as follows:

1. **Constants:** Any module-level constants or configuration variables should be defined at the top. This makes it easy for users to find and modify them if needed.
2. **Classes:** If a module contains any class definitions, they should appear first. Classes define the core structure and behavior of the module.
3. **Functions:** Public functions follow the class definitions. These functions are the primary operations or utilities that the module offers for external use.
4. **Hidden Functions:** Internal functions (those with a leading underscore) come last. These are used for supporting internal logic and are not intended to be accessed directly by users.

This ordering helps ensure that users interacting with the module can quickly identify the main components, while hidden/internal logic remains at the bottom for a clearer separation of concerns.

Development Tools
-----------------
For ease of development, tools and dependencies for linting, formatting, spellchecking, testing, and documentation building are included as optional dependencies. Installing these is as simple as running the following::

    pip install -e .[dev]

In addition, developers should use `nox` to automate many tasks:

* `nox -s tests` - run tests with coverage reports
* `nox -s linter` - lint and format the code
* `nox -s codespell` - check for and fix misspellings
* `nox -s pre-commit` - run pre-commit checks (all above)
* `nox -s docs` - build the documentation

Use these tools to ensure the code remains clean and follows best practices.
