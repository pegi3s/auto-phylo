#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

remove_stops_autop_version = "4.0.0"
remove_stops_seda_docker_version = "1.7.5-docker29.0.1"
remove_stops_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global remove_stops_autop_version, remove_stops_seda_docker_version, remove_stops_seda_program_version
    global seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "remove_stops_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    docker_c_version = config["remove_stops_seda_docker_c_version"]

    if docker_c_version:
        remove_stops_autop_version = "?"
        remove_stops_seda_docker_version = docker_c_version
        remove_stops_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{remove_stops_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    step1_dir = f"/data/{prefix}1-Remove_stop_codons"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    subprocess.run(start + ["remove-stop-codons", "-id", f"/data/{input_dir}", "-od", step1_dir,
                             "-rlb", "-lb", "unix"], stdout=subprocess.DEVNULL)
    for f in glob.glob(f"{step1_dir}/*"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*remove_stops", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'remove_stops {remove_stops_autop_version},pegi3s/seda:{remove_stops_seda_docker_version},'
                     f'SEDA {remove_stops_seda_program_version},"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Removing stop codons", flush=True)
    main()
