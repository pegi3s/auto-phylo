#!/usr/bin/env python3
import os
import re
import subprocess
import sys

merge_autop_version = "4.0.0"
merge_seda_docker_version = "1.7.5-docker29.0.1"
merge_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global merge_autop_version, merge_seda_docker_version, merge_seda_program_version, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "merge_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    docker_c_version = config["merge_seda_docker_c_version"]

    if docker_c_version:
        merge_autop_version = "?"
        merge_seda_docker_version = docker_c_version
        merge_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{merge_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    step1_dir = f"/data/{prefix}1-merge_files"
    os.makedirs(step1_dir, exist_ok=True)
    print("Merging files")
    subprocess.run(start + ["merge", "-id", f"/data/{input_dir}", "-od", step1_dir,
                             "-n", "merge_output", "-rlb", "-lb", "unix", "-sc", "original"])

    step2_dir = f"/data/{prefix}2-redundant_sequences"
    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    os.makedirs(step2_dir, exist_ok=True)
    print("Removing redundant sequences")
    subprocess.run(start + ["remove-redundant", "-id", step1_dir, "-od", f"/data/{out_dir}",
                             "-rs", "-smh", step2_dir])

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*merge", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'merge {merge_autop_version},pegi3s/seda:{merge_seda_docker_version},'
                     f'SEDA {merge_seda_program_version},"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    main()
