import subprocess
from dataclasses import dataclass, replace
from enum import Enum
from functools import total_ordering, wraps
from operator import attrgetter
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import bitmath


@total_ordering
@dataclass(slots=True, frozen=True)
class Result:
    path: Path
    size: bitmath.Bitmath
    match_description: str

    def __lt__(self, other: "Result") -> bool:
        return (self.size, len(other.path.name)) < (other.size, len(self.path.name))


@total_ordering
@dataclass(slots=True, frozen=True)
class ImageDimension:
    height: int
    width: int

    @classmethod
    def from_str(cls, s: str) -> "ImageDimension":
        """
        given a string 2320x3088, return a dimension where the left is the height
        and the right is the width
        """
        return cls(*map(int, s.lower().split("x")))

    @property
    def pixels(self) -> int:
        return self.height * self.width

    def __lt__(self, other: "ImageDimension") -> bool:
        return self.pixels < other.pixels


@total_ordering
@dataclass(slots=True, frozen=True)
class ImageResult(Result):
    dimension: ImageDimension

    def __lt__(self, other: "ImageResult") -> bool:
        return (self.dimension, self.size, len(other.path.name)) < (
            other.dimension,
            other.size,
            len(self.path.name),
        )


@dataclass(slots=True, frozen=True)
class ResultGroup:
    results: list[Result]

    @classmethod
    def new(cls) -> "ResultGroup":
        return cls([])

    @property
    def best(self) -> Optional[Result]:
        if self.results:
            return self.results[-1]

    def inferior_results(self) -> Iterable[Result]:
        for result in self.results[:-1]:
            if "very high" in result.match_description.lower():
                yield result

    def add(self, r: Result) -> "ResultGroup":
        results = [*self.results, r]
        results.sort()
        return replace(self, results=results)

    def __bool__(self) -> bool:
        return bool(self.results)


def wrap_subprocess_errors(
    fn: Callable[
        ...,
        Any,
    ]
):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:

            return fn(self, *args, **kwargs)
        except subprocess.CalledProcessError as exc:
            raise self.Error(exc.stderr) from exc

    return wrapper


@dataclass(slots=True, frozen=True)
class Czkawka:
    czkawka_path: str
    search_directories: list[Path]

    class CommandNames(Enum):
        IMAGE = "image"
        VIDEO = "video"

    class Error(Exception):
        pass

    @wrap_subprocess_errors
    def run(self, command: CommandNames, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                self.czkawka_path,
                command.value,
                "--directories",
                *map(Path.as_posix, self.search_directories),
                *args,
            ],
            text=True,
            capture_output=True,
            check=True,
        )

    def image(self) -> Iterable[ResultGroup]:
        cmd_result = self.run(self.CommandNames.IMAGE)
        group = ResultGroup.new()

        for line in cmd_result.stdout.split("\n"):
            try:
                # "{filepath} - {dimensions} - {size} - {match_description}"
                *path_parts, dimesions, size, match_description = line.split(" - ")
            except ValueError:
                # if there's a group and the line can't be parsed
                # then we've completed a group and we should yield it
                # then create a new group and continue on
                if group:
                    yield group
                    group = ResultGroup.new()
            else:
                result = ImageResult(
                    path=Path("".join(path_parts)),
                    dimension=ImageDimension.from_str(dimesions),
                    size=bitmath.parse_string(size).best_prefix(),
                    match_description=match_description,
                )
                assert result.path.exists()
                group = group.add(result)

        if group:
            yield group

    def video(
        self,
        minimum_file_size: bitmath.Bitmath = bitmath.Byte(1),
    ) -> Iterable[ResultGroup]:
        cmd_result = self.run(
            self.CommandNames.VIDEO,
            "--minimal-file-size",
            str(minimum_file_size.bytes),
        )
        group = ResultGroup.new()

        for line in cmd_result.stdout.split("\n"):
            try:
                # "{filepath} - {size}"
                *path_parts, size = line.split(" - ")

                if not path_parts:
                    raise ValueError()

            except ValueError:
                # if there's a group and the line can't be parsed
                # then we've completed a group and we should yield it
                # then create a new group and continue on
                if group:
                    yield group
                    group = ResultGroup.new()
            else:
                result = Result(
                    path=Path("".join(path_parts)),
                    size=bitmath.parse_string(size).best_prefix(),
                    match_description="very high",
                )
                assert result.path.exists()
                group = group.add(result)

        if group:
            yield group

    def duplicates(self) -> Iterable[Path]:
        for group in self.image():
            yield from map(attrgetter("path"), group.inferior_results())

        for group in self.video():
            yield from map(attrgetter("path"), group.inferior_results())
