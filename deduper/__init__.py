"""
Wrapper around czkawka
TODO FIXME
"""

from pathlib import Path

from typer import Typer, echo

from deduper.czkawka import Czkawka

cli = Typer()
main = cli


@cli.command()
def list_duplicates(directory: Path = Path.cwd()):
    """
    prints the absolute path of all duplicate files underneath the current working directory.
    """
    for dup in Czkawka("czkawka_cli", [directory]).duplicates():
        echo(dup.as_posix())


@cli.command()
def list_best(directory: Path = Path.cwd()):
    """
    TODO
    """
    for best in Czkawka("czkawka_cli", [directory]).best():
        echo(best.as_posix())


if __name__ == "__main__":
    cli()
