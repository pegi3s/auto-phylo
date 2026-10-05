#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys

fasttree_autop_version = "4.0.0"
fasttree_docker_version = "2.2.0"
fasttree_program_version = "2.2.0"
fasttree_ref = "Price, M. N., Dehal, P. S., & Arkin, A. P. (2009)"
fasttree_doi = "10.1093/molbev/msp077"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global fasttree_autop_version, fasttree_docker_version, fasttree_program_version
    global fasttree_ref, fasttree_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "fasttree_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    docker_c_version = config["fasttree_docker_c_version"]

    if docker_c_version:
        fasttree_autop_version = "?"
        fasttree_docker_version = docker_c_version
        fasttree_program_version = "?"
        fasttree_ref = "?"
        fasttree_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-Fasttree_tree"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(f"/data/{out_dir}", exist_ok=True)

    # FastTree writes the tree to stdout, so it must be redirected inside the container
    shell_cmd = f"FastTree -nt -gtr -gamma /data/{input_dir}/{file_name} > {step1_dir}/{file_name}.tree"
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/fasttree:{fasttree_docker_version}", "bash", "-c", shell_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.copy(f"{step1_dir}/{file_name}.tree", f"/data/{out_dir}/{file_name}.nwk")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*Fasttree", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Fasttree {fasttree_autop_version},pegi3s/fasttree:{fasttree_docker_version},'
                     f'Fasttree {fasttree_program_version},"{fasttree_ref}","{fasttree_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'fasttree_ref="{fasttree_ref}"\nfasttree_doi="{fasttree_doi}"\n')


if __name__ == "__main__":
    print("ML tree inference using Fasttree", flush=True)
    main()
