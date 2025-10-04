#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Compact all VirtualBox disk images and report results."""
import os
import subprocess
import sys
from typing import overload, Literal, Iterator

from pathlib import Path

if sys.platform != "win32":
    raise RuntimeError("This utility currently only supports Windows.")

HOMEDIR = Path(os.environ["USERPROFILE"])
PROGRAM = Path("C:/Program Files/Oracle/VirtualBox/VBoxManage.exe")
VBOX_DIR = HOMEDIR / "VirtualBox VMs"


@overload
def run_manage_command(args: list[str | Path], capture: Literal[False]) -> None:
    ...


@overload
def run_manage_command(args: list[str | Path], capture: Literal[True]) -> str:
    ...


def run_manage_command(args: list[str | Path], capture: bool) -> str | None:
    """Run VBoxManage command.

    Arguments:
        args: List of command line arguments to pass to the program.
        capture: Whether or not to capture command line output from
            the program.

    Returns:
        None if capture is False, otherwise the command's standard
        output as a string.
    """
    try:
        result = subprocess.run(
            [PROGRAM, *args],
            capture_output=capture,

            check=True,
            shell=False
        )
    except subprocess.CalledProcessError as exc:
        if capture:
            print(exc.stderr.decode("utf-8"), sys.stderr)
        raise

    if capture:
        return result.stdout.decode("UTF-8").replace("\r\n", "\n")
    return None


def split_colon_line(line: str) -> tuple[str, str]:
    """Splits a colon separated line into the left and right elements

    Arguments:
        line: The line to split

    Returns:
        Tuple of the stripped left and right sides of the colon.

    """
    key, _, value = line.partition(":")
    return (key.strip(), value.strip())


def get_disks() -> Iterator[tuple[Path, str]]:
    """Get a dictionary of all disks known to virtualbox.

    Yields:
       Tuples of information about each disk. The first element of the
       tuple is the path to the disk, and the second element is the
       format of the disk.
    """
    disk_str = run_manage_command(["list", "hdds"], True)
    chunks = disk_str.strip().split("\n\n")

    for chunk in chunks:
        lines = chunk.splitlines()
        info_dict = dict(split_colon_line(line) for line in lines)
        yield Path(info_dict["Location"]), info_dict["Storage format"]


def human_size(orig_value: int) -> str:
    """Convert from integer bytes to human readable size.

    Arguments:
        orig_value: The value in bytes

    Returns:
        Human readable string of the size.

    """
    val_strs = ["B", "KiB", "MiB", "GiB", "TiB"]
    new_value = float(orig_value)
    val_id = 0
    while new_value > 1024 and val_id < len(val_strs) - 1:
        new_value /= 1024
        val_id += 1

    return f"{new_value:.2f}{val_strs[val_id]}"


def compact_disk(location: Path) -> None:
    """Compact a single VDI disk.

    Warning:
        This will fail if trying to compact a disk that is not
        in the VDI format.__annotations__

    Arguments:
        location: The path to the disk to compact

    """
    orig_size = location.stat().st_size
    print(f"Compacting {location}")
    run_manage_command(["modifymedium", "--compact", location], False)
    new_size = location.stat().st_size
    print(f"\tOriginal Size       : {human_size(orig_size)}")
    print(f"\tNew Size            : {human_size(new_size)}")
    percent_orig = new_size / orig_size * 100
    print(f"\tPercent of original : {percent_orig:.2f}%")


def main() -> None:
    """Compact all VirtualBox disks and report results."""

    for path, disk_type in get_disks():
        if disk_type != "VDI":
            print(f"Skipping non-VDI disk {path}")
            continue
        compact_disk(path)


if __name__ == "__main__":
    main()
