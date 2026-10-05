#!/usr/bin/env python3
import glob
import os
import shutil
import subprocess
import sys

from module_utils import get_module_def, load_module_defs, resolve_module_path

main_autop_version = "4.0.0"

DATA = "/data"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def run_module(command, args):
    path = resolve_module_path(command)
    if path is None:
        sys.exit(f"This is an invalid command: {command}")
    subprocess.run([path, *args], check=True)


def copy_entry(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy(src, dst)


def copy_matches(output_dir, pattern, dest):
    """Copy every file/dir matching `pattern` inside `output_dir` to `dest`."""
    matches = sorted(glob.glob(os.path.join(output_dir, pattern)))
    if not matches:
        return False
    if len(matches) == 1:
        copy_entry(matches[0], dest)
    else:
        for idx, match in enumerate(matches, 1):
            copy_entry(match, f"{dest}.{idx}")
    return True


def keep_files(mdef, command, output_dir, raw_output, project, block, q, files_to_keep):
    """Copy the module's output files into files_to_keep, as defined by module_defs.conf."""
    def dest_path(suffix_template):
        suffix = suffix_template.format(raw_output=raw_output, block=block) if suffix_template else ""
        name = ".".join([str(q), command] + ([suffix] if suffix else []) + [block])
        return os.path.join(files_to_keep, name)

    copied = False

    if mdef["keep_if_exists"]:
        pattern, suffix = mdef["keep_if_exists"]
        copied = copy_matches(output_dir, pattern, dest_path(suffix))

    if not copied:
        for pattern, suffix in mdef["keep_else"]:
            copied = copy_matches(output_dir, pattern, dest_path(suffix)) or copied

    for pattern, suffix in mdef["keep"]:
        copied = copy_matches(output_dir, pattern, dest_path(suffix)) or copied

    for path_template, suffix in mdef["keep_extra"]:
        path = os.path.join(f"{DATA}/{project}/intermediate_files", path_template.format(block=block))
        if os.path.isfile(path):
            copy_entry(path, dest_path(suffix))
            copied = True

    return copied


def main():
    project = read_config("project")["project"]
    module_defs = load_module_defs()

    project_dir = f"{DATA}/{project}"
    files_to_keep = f"{DATA}/files_to_keep"
    intermediate_files = f"{project_dir}/intermediate_files"

    os.makedirs(f"{intermediate_files}/refs", exist_ok=True)
    os.makedirs(files_to_keep, exist_ok=True)
    shutil.copy(f"{DATA}/pipeline", files_to_keep)
    shutil.copy(f"{DATA}/config", files_to_keep)
    with open(f"{files_to_keep}/versions.csv", "w") as f:
        f.write("Module version,Docker image version,Program version,Reference,DOI\n")

    run_module("pipeline_drawing", [])
    shutil.move(f"{DATA}/Pipeline.gv.svg", f"{files_to_keep}/Pipeline.svg")

    with open(f"{DATA}/pipeline") as f:
        pipeline_lines = [line for line in f.read().splitlines() if line.strip()]

    blocks_and_commands_path = f"{intermediate_files}/blocks_and_commands"

    i = 0
    j = 1
    q = 1
    old_output = None

    with open(blocks_and_commands_path, "a") as blocks_and_commands:
        for line in pipeline_lines:
            fields = line.split(maxsplit=4)
            fields += [""] * (5 - len(fields))
            command, raw_input, raw_output, split, dir_number = fields

            mdef = get_module_def(module_defs, command)

            input_path = f"{project}/{raw_input}"
            output_path = f"{project}/{raw_output}"

            if not os.path.isdir(f"{project_dir}/{raw_input}"):
                copy_entry(f"{DATA}/{raw_input}", f"{project_dir}/{os.path.basename(raw_input)}")

            if old_output != input_path:
                i += 1
                j = 1
            else:
                j += 1

            block = f"B{i}C{j}"
            prefix = f"{project}/intermediate_files/{block}/{block}-"

            blocks_and_commands.write(" ".join([command, raw_input, raw_output, split, dir_number, block]) + "\n")
            blocks_and_commands.flush()

            if split == "split" and mdef["split"]:
                run_module("split", [input_path, dir_number])
                for n in range(1, int(dir_number) + 1):
                    run_module(command, [f"{input_path}.{n}", output_path, f"{prefix}R{n}-"])
                    shutil.rmtree(f"{DATA}/{input_path}.{n}", ignore_errors=True)
            else:
                run_module(command, [input_path, output_path, prefix])
            old_output = output_path

            output_dir = f"{DATA}/{output_path}"
            if keep_files(mdef, command, output_dir, raw_output, project, block, q, files_to_keep):
                q += 1

    shutil.copy(blocks_and_commands_path, files_to_keep)
    run_module("pipeline_summary", [])

    for filename in os.listdir(DATA):
        project_entry = f"{project_dir}/{filename}"
        if os.path.isdir(project_entry):
            shutil.rmtree(project_entry)
        elif os.path.isfile(project_entry):
            os.remove(project_entry)


if __name__ == "__main__":
    main()


