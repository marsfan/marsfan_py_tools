#!/usr/bin/env Python3
# -*- coding: UTF-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https: //mozilla.org/MPL/2.0/.
"""Simple tool to upgrade pip installed packages.

On Windows, also supports using the Python launcher to select the Python
version to use.

"""

# TODO: Support versioning on other platforms?
from collections.abc import Iterable
import subprocess
import re
from argparse import ArgumentParser, ArgumentTypeError, Namespace
import sys
import json

# TODO: Argument to just print out updated
# TODO:use pip's --report option with --dry-run to list all upgrades (even eager)


class ArgNamespace(Namespace):
    """Argument namespace. Helps with type hinting."""

    version: str | None = None
    """Optional version string for Python version to use.

    Currently only supports Windows.
    """

    not_required: bool = False
    """Whether or not to only upgrade packages that are not dependencies of other packages."""

    eager: bool = False
    """Whether or not to perform eager upgrade on packages.

    Has no affect if :py:attr:`no_required` is false since in that case
    all packages are already being upgraded.
    """

    yes: bool = False
    """Don't ask for confirmation prior to starting package upgrade."""


def run_pip_command(version: str | None, args: Iterable[str], capture_output: bool) -> str:
    """Run a pip command, and return standard output.

    Arguments:
        version: Python version to run. If :py:type:`None`, default
            Python version will be used. This has no affect on
            non-Windows platforms, where the default version is always
            used.
        args: Arguments to pass to pip.
        capture_output: If true, capture standard output from running the
            command and return it.

    Returns:
        The standard output from running the command if capture_output
        is True, otherwise returns an empty string.

    """
    if sys.platform == "win32" and version:
        command = ["py", version, "-m", "pip"]
    elif sys.platform == "win32":
        command = ["py", "-m", "pip"]
    else:
        command = ["python3", "-m", "pip"]
    command.extend(args)
    result = subprocess.run(
        command,
        check=True,
        shell=False,
        capture_output=capture_output
    )

    if capture_output:
        return result.stdout.decode("UTF-8")
    else:
        return ""


def parse_version_flag(argument: str) -> str:
    """Parse -A.B argument syntax like the Python Pindows launcher does.

    Arguments:
        argument: The argument to parse

    Returns:
        Value of the parsed argument

    """
    result = re.fullmatch(r"-(\d(\.\d+)?)", argument)
    if not result:
        raise ArgumentTypeError("Invalid Python version string")
    return argument


def get_outdated(version: str | None, not_required: bool) -> list[str]:
    """Get a list of packages that are outdated.

    Arguments:
        version: Python version to use for upgrading. If :py:type:`None`,
            default Python version will be used. This has no affect on
            non-Windows platforms, where the default version is always
            used


    Returns:
        List of outdated packages.

    """
    pip_args = ["list", "--outdated", "--format=json"]
    if not_required:
        pip_args.append("--not-required")
    command_out = run_pip_command(version, pip_args, True)
    return [pkg["name"] for pkg in json.loads(command_out)]


def confirm_upgrade(packages: list[str], eager_warning: bool) -> bool:
    """Print out package upgrade list, and confirm upgrade from user.

    Arguments:
        packages: List of packages to upgrade.
        eager_warning: If True, also prints out a warning that eager upgrading
            of dependencies will also be performed.

    """
    print("The following packages are found to be outdated:")

    for package in packages:
        print(f"\t{package}")

    print("")
    if eager_warning:
        print(
            "WARNING: Eager flag supplied. Additional packages beyond these will be upgraded"
        )
    return input("Proceed (Y/n)? ").lower() == "y"


def upgrade_packages(version: str | None, packages: list[str], eager: bool) -> None:
    """Upgrade the specified packages.

    Arguments:
        version: Python version to use for upgrading. If :py:type:`None`,
            default Python version will be used. This has no affect on
            non-Windows platforms, where the default version is always
            used
        packages: List of packages to upgrade.
        eager: If true, use eager upgrade strategy, which upgrades all
            dependencies as well.

    """
    command = ["install", "-U", "--dry-run"]
    if eager:
        command.append("--upgrade-strategy=eager")
    command.extend(packages)
    run_pip_command(version, command, False)


def main() -> None:
    """Upgrade pip installed packages."""
    parser = ArgumentParser(description="Update all outdated Python packages.")
    if sys.platform == "win32":
        parser.add_argument(
            "version",
            type=parse_version_flag,
            nargs="?",
            help="Python version to update packages for. Pass -0 to list versions. Does not work with free-threaded specifiers"
        )
    parser.add_argument(
        "-n",
        "--not-required",
        action="store_true",
        help="Only upgrade packages that are not required by other packages"
    )
    parser.add_argument(
        "-e",
        "--eager",
        action="store_true",
        help="Eagerly upgrade dependent packages. Only has an affect of --not-required is also set"
    )
    parser.add_argument(
        "--yes",
        "-y",

        action="store_true",
        help="Don't ask for confirmation prior to upgrading packages."
    )

    args = parser.parse_args(namespace=ArgNamespace())

    if sys.platform == "win32" and args.version == "-0":
        subprocess.run(["pya", "-0"], check=False, shell=False)
    else:
        outdated = get_outdated(args.version, args.not_required)
        if confirm_upgrade(outdated, args.eager and args.not_required) or args.yes:
            upgrade_packages(args.version, outdated, args.eager)
        else:
            print("Upgrade cancelled")
