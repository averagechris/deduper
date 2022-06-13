import pytest
from typer.testing import CliRunner

import deduper


@pytest.fixture(scope="session")
def typer():
    return CliRunner()


@pytest.fixture
def cli(typer):
    def runner(*args: str, **kwargs):
        return typer.invoke(deduper.cli, args)

    return runner


def test_help_runs(cli):
    assert cli("--help").exit_code == 0

    res = cli()
    assert res.exit_code == 2
    assert "Usage: " in res.output


@pytest.mark.xfail
def test_empty_duplicates(cli, test_files):
    # TODO FIXME
    res = cli("duplicates", "--directory", test_files.as_posix())
    assert res.exit_code == 0
