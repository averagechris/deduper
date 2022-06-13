import shutil
import stat
from pathlib import Path

import pytest


def copy_test_files_to(p: Path):
    root_dir = Path.cwd()

    while not root_dir.joinpath("pyproject.toml").exists() and root_dir != Path("/"):
        root_dir = root_dir.parent

    shutil.copytree(
        root_dir.joinpath("tests/data").as_posix(),
        p.as_posix(),
        dirs_exist_ok=True,
    )


@pytest.fixture
def slow_test_files_factory(tmp_path_factory: pytest.TempPathFactory):
    """
    returns a Path of a temp directory with all of the test files copied
    into it. the copy runs each time this fixture is invoked, so it's expensive.
    """

    def factory():
        tmp_dir = tmp_path_factory.mktemp("duplicates")
        copy_test_files_to(tmp_dir)
        return tmp_dir

    return factory


@pytest.fixture
def slow_test_files(slow_test_files_factory):
    return slow_test_files_factory()


@pytest.fixture(scope="session")
def test_files(tmp_path_factory: pytest.TempPathFactory):
    """
    Returns an "immutable" path containing all of the test files.
    This path is only copied into once per test session, so it's
    marked as read only so the contents are not accidentally changed causing
    impure tests.
    """

    tmp_dir = tmp_path_factory.mktemp("immutable_duplicates")
    copy_test_files_to(tmp_dir)

    original_st_mode = tmp_dir.stat().st_mode
    read_only_mask = 0o777 ^ (stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH)
    tmp_dir.chmod(original_st_mode & read_only_mask)

    yield tmp_dir

    tmp_dir.chmod(original_st_mode)
    shutil.rmtree(tmp_dir)
