import os
import shutil
import pathlib

from warnings import catch_warnings, filterwarnings


def download_templates(path: str | os.PathLike | None = None) -> None:
    """
    Copy example templates to into a local directory.

    Parameters
    ----------
    path : str or PathLike or None, optional
        Path to parent directory where a new `thevenin_templates` folder will
        be created and example templates will be copied to. If None (default),
        the current working directory is used.

    """
    resources = pathlib.Path(os.path.dirname(__file__), '_resources')

    path = pathlib.Path(path or '.').joinpath('thevenin_templates')
    path.mkdir(parents=True, exist_ok=True)

    for name in list_templates():
        orig = resources.joinpath(name)
        new = path.joinpath(name)

        shutil.copy(orig, new)


def list_templates() -> list[str]:
    """
    List names of available example templates.

    Returns
    -------
    names : list[str]
        A list of example file names from an internal `resources` folder.

    """
    resources = pathlib.Path(os.path.dirname(__file__), '_resources')
    return os.listdir(resources)


def load_templates(*names: str) -> dict:
    """
    Load example templates by name.

    Parameters
    ----------
    *names : str
        One or more names of example template files to load. See options with
        `list_templates()`.

    Returns
    -------
    templates : dict or tuple[dict]
        A single template dictionary if one name is provided, or a tuple of
        template dictionaries in the same order as the given `names`.

    Raises
    ------
    FileNotFoundError
        Requested template name is not available.

    """
    from thevenin._basemodel import _yaml_reader

    available = list_templates()
    resources = pathlib.Path(os.path.dirname(__file__), '_resources')

    templates = []
    for name in names:
        if not name.endswith('.yaml'):
            name += '.yaml'

        if name not in available:
            raise FileNotFoundError(f"{name} is not an available template.")

        with catch_warnings():
            filterwarnings('ignore', message='.*Using the default.*')
            template = _yaml_reader(resources.joinpath(name))

        templates.append(template)

    if len(templates) == 1:
        return templates[0]

    return tuple(templates)


def print_templates(name: str) -> None:
    """
    Print example templates.

    Parameters
    ----------
    name : str
        Name of a template file to print. See options with `list_templates()`.

    Raises
    ------
    FileNotFoundError
        Requested template name is not available.

    """
    available = list_templates()
    resources = pathlib.Path(os.path.dirname(__file__), '_resources')

    if not name.endswith('.yaml'):
        name += '.yaml'

    if name not in available:
        raise FileNotFoundError(f"{name} is not an available template.")

    print('=' * 30, name, '=' * 30, sep='\n')
    with open(resources.joinpath(name), 'r') as f:
        print(f.read())
