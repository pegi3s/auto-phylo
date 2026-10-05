#!/usr/bin/env python3
import os
import re
import subprocess
import sys

add_refs_autop_version = "4.0.0"
add_refs_seda_docker_version = "1.7.5-docker29.0.1"
add_refs_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global add_refs_autop_version, add_refs_seda_docker_version, add_refs_seda_program_version, seda_ref, seda_doi

    input_dir, out_dir = sys.argv[1], sys.argv[2]

    config = read_config("dir", "project", "add_refs_reference", "add_refs_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    reference = config["add_refs_reference"]
    docker_c_version = config["add_refs_seda_docker_c_version"]

    if docker_c_version:
        add_refs_autop_version = "?"
        add_refs_seda_docker_version = docker_c_version
        add_refs_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{add_refs_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    subprocess.run(["cp", f"/data/{reference}", f"/data/{input_dir}"], check=True)
    subprocess.run(start + ["merge", "-id", f"/data/{input_dir}", "-od", f"/data/{out_dir}",
                             "-n", "refseq_added", "-rlb", "-lb", "unix", "-sc", "original"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(f"/data/{input_dir}/{reference}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*add_refs", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'add_refs {add_refs_autop_version},pegi3s/seda:{add_refs_seda_docker_version},'
                     f'SEDA {add_refs_seda_program_version},"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Adding reference sequences", flush=True)
    main()
