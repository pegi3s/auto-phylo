#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

get_phylo_taxa_autop_version = "4.0.0"
get_phylo_taxa_seda_docker_version = "1.7.5-docker29.0.1"
get_phylo_taxa_seda_program_version = "1.7.5"
get_phylo_taxa_utilities_docker_version = "0.25.0"
get_phylo_taxa_utilities_program_version = "0.25.0"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global get_phylo_taxa_autop_version, get_phylo_taxa_seda_docker_version, get_phylo_taxa_seda_program_version
    global get_phylo_taxa_utilities_docker_version, get_phylo_taxa_utilities_program_version, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "get_phylo_taxa_name1", "get_phylo_taxa_name2",
                          "get_phylo_taxa_seda_docker_c_version", "get_phylo_taxa_utilities_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    name1 = config["get_phylo_taxa_name1"]
    name2 = config["get_phylo_taxa_name2"]

    if config["get_phylo_taxa_seda_docker_c_version"]:
        get_phylo_taxa_autop_version = "?"
        get_phylo_taxa_seda_docker_version = config["get_phylo_taxa_seda_docker_c_version"]
        get_phylo_taxa_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    if config["get_phylo_taxa_utilities_docker_c_version"]:
        get_phylo_taxa_autop_version = "?"
        get_phylo_taxa_utilities_docker_version = config["get_phylo_taxa_utilities_docker_c_version"]
        get_phylo_taxa_utilities_program_version = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{get_phylo_taxa_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    step1_dir = f"/data/{prefix}1-Phyloselected"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(f"/data/{out_dir}", exist_ok=True)

    # unexpanded globs are passed through as-is if there is no match, matching bash's default behaviour
    nuc_files = sorted(glob.glob(f"/data/{input_dir}/*.nuc_aligned")) or [f"/data/{input_dir}/*.nuc_aligned"]
    nwk_files = sorted(glob.glob(f"/data/{input_dir}/*.nwk")) or [f"/data/{input_dir}/*.nwk"]

    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/utilities:{get_phylo_taxa_utilities_docker_version}", "get_phylo_taxa",
                    name1, name2] + nuc_files + nwk_files,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in glob.glob(f"/data/{input_dir}/*.excluding"):
        shutil.move(f, step1_dir)
    for f in glob.glob(f"/data/{input_dir}/*.only"):
        shutil.move(f, step1_dir)

    subprocess.run(start + ["undo-alignment", "-id", step1_dir, "-od", step1_dir],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in glob.glob(f"{step1_dir}/*.only"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*get_phylo_taxa", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'get_phylo_taxa {get_phylo_taxa_autop_version},pegi3s/seda:{get_phylo_taxa_seda_docker_version},'
                     f'SEDA {get_phylo_taxa_seda_program_version},"{seda_ref}","{seda_doi}"\n')
            f.write(f',pegi3s/utilities:{get_phylo_taxa_utilities_docker_version},'
                    f'utilities {get_phylo_taxa_utilities_program_version},,\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Getting sequences from phylogeny", flush=True)
    main()
