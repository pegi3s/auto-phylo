#!/usr/bin/env python3
"""Shared helpers for resolving /opt modules and reading module_defs.conf.

Imported by both `pre_main` and `main` so that module scripts can be named
either "command" or "command.py", and so that per-module behaviour (whether a
module supports the "split"/block feature and which output files should be
copied to files_to_keep) is driven by module_defs.conf instead of being
hard-coded.
"""
import os

MODULE_DEFS_PATH = "/opt/module_defs.conf"

DEFAULT_MODULE_DEF = {"split": False, "keep": [], "keep_extra": [], "keep_if_exists": None, "keep_else": []}


def resolve_module_path(command, base="/opt"):
    """Return the path to run for `command`, accepting both "command" and "command.py"."""
    for candidate in (command, f"{command}.py"):
        path = os.path.join(base, candidate)
        if os.path.isfile(path):
            return path
    return None


def _split_pattern_dest(value):
    pattern, _, dest = value.partition("=>")
    return pattern.strip(), dest.strip()


def load_module_defs(path=MODULE_DEFS_PATH):
    """Parse module_defs.conf into {module_name: {split, keep, keep_extra, keep_if_exists, keep_else}}."""
    defs = {}
    if not os.path.isfile(path):
        return defs

    current = None
    with open(path) as f:
        for raw_line in f:
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                current = defs.setdefault(line[1:-1].strip(), {
                    "split": False, "keep": [], "keep_extra": [], "keep_if_exists": None, "keep_else": [],
                })
                continue
            if current is None or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key == "split":
                current["split"] = value.lower() in ("yes", "true", "1")
            elif key in ("keep", "keep_extra", "keep_else"):
                current[key].append(_split_pattern_dest(value))
            elif key == "keep_if_exists":
                current[key] = _split_pattern_dest(value)
    return defs


def get_module_def(defs, command):
    return defs.get(command, DEFAULT_MODULE_DEF)
