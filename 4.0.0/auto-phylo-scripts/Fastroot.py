#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

fastroot_autop_version = "4.0.0"
fastroot_docker_version = "1.5"
fastroot_program_version = "1.5"
fastroot_ref = "Mai, U., Sayyari, E., & Mirarab, S. (2017)"
fastroot_doi = "10.1371/journal.pone.0182238"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global fastroot_autop_version, fastroot_docker_version, fastroot_program_version
    global fastroot_ref, fastroot_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "fastroot_rooting_method", "fastroot_outgroup",
                          "fastroot_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    rooting_method = config["fastroot_rooting_method"]
    outgroup = config["fastroot_outgroup"]
    docker_c_version = config["fastroot_docker_c_version"]

    if docker_c_version:
        fastroot_autop_version = "?"
        fastroot_docker_version = docker_c_version
        fastroot_program_version = "?"
        fastroot_ref = "?"
        fastroot_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-FastRoot_tree_rooting"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(f"/data/{out_dir}", exist_ok=True)

    cmd = ["docker", "run", "--rm", "-v", f"{data_dir}:/data", f"pegi3s/fastroot:{fastroot_docker_version}",
           "-i", f"/data/{input_dir}/{file_name}", "-m", rooting_method]
    if rooting_method in ("og", "OG"):
        cmd += ["-g", outgroup]
    cmd += ["-o", f"{step1_dir}/{file_name}_rooted.nwk"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in glob.glob(f"{step1_dir}/*_rooted.nwk"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*FastRoot", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'FastRoot {fastroot_autop_version},pegi3s/fastroot:{fastroot_docker_version},'
                     f'FastRoot {fastroot_program_version},"{fastroot_ref}","{fastroot_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'fastroot_ref="{fastroot_ref}"\nfastroot_doi="{fastroot_doi}"\n')


if __name__ == "__main__":
    print("Rooting the tree with Fastroot", flush=True)
    main()
