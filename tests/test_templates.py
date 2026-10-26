import pytest
import thevenin as thev


def test_download_templates(tmp_path):

    dest = tmp_path.joinpath('thevenin_templates')
    thev.download_templates(tmp_path)
    assert dest.is_dir()

    expected_files = thev.list_templates()
    actual_files = [p.name for p in dest.iterdir()]
    assert set(expected_files) == set(actual_files)


def test_list_templates():
    from thevenin._templates import RESOURCES

    names = thev.list_templates()
    assert isinstance(names, list)
    assert all(isinstance(n, str) for n in names)
    assert len(names) > 0

    for name in names:
        assert RESOURCES.joinpath(name).is_file()


def test_load_templates():

    # test invalid names
    with pytest.raises(FileNotFoundError):
        thev.load_templates('fake')

    with pytest.raises(FileNotFoundError):
        thev.load_templates('fake.yaml')

    available = thev.list_templates()
    single_name = available[0]
    multiple_names = [single_name, single_name]

    # test single load
    template = thev.load_templates(single_name)
    assert isinstance(template, dict)

    # make sure the template works
    sim = thev.Simulation(template)
    assert isinstance(sim, thev.Simulation)

    pred = thev.Prediction(template)
    assert isinstance(pred, thev.Prediction)

    # test multiple load
    templates = thev.load_templates(*multiple_names)
    assert len(templates) == len(multiple_names)
    assert isinstance(templates, tuple)

    for key, value in templates[0].items():
        if not callable(value):
            assert templates[1][key] == value


def test_print_templates(capsys):

    # test invalid names
    with pytest.raises(FileNotFoundError):
        thev.print_templates('fake.yaml')

    # capture output and test
    available = thev.list_templates()
    name = available[0].removesuffix('.yaml')

    thev.print_templates(name)
    captured = capsys.readouterr()

    assert name in captured.out
    assert len(captured.out.strip()) > len(name)
