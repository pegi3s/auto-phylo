#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

clustalomega_autop_version = "4.0.0"
clustalomega_docker_version = "1.2.4"
clustalomega_program_version = "1.2.4"
clustalomega_seda_docker_version = "1.7.5-docker29.0.1"
clustalomega_seda_program_version = "1.7.5"
clustalomega_ref = "Sievers, F., & Higgins, D. G. (2014)"
clustalomega_doi = "10.1002/0471250953.bi0313s48"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global clustalomega_autop_version, clustalomega_docker_version, clustalomega_program_version
    global clustalomega_seda_docker_version, clustalomega_seda_program_version, clustalomega_ref, clustalomega_doi
    global seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "clustalomega_docker_c_version", "clustalomega_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["clustalomega_docker_c_version"]:
        clustalomega_autop_version = "?"
        clustalomega_docker_version = config["clustalomega_docker_c_version"]
        clustalomega_program_version = "?"
        clustalomega_ref = "?"
        clustalomega_doi = "?"

    if config["clustalomega_seda_docker_c_version"]:
        clustalomega_autop_version = "?"
        clustalomega_seda_docker_version = config["clustalomega_seda_docker_c_version"]
        clustalomega_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{clustalomega_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    file_name = os.listdir(f"/data/{input_dir}")[0]
    step1_dir = f"/data/{prefix}1-CO_sequence_alignment"
    os.makedirs(step1_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/clustalomega:{clustalomega_docker_version}",
                    "-i", f"/data/{input_dir}/{file_name}",
                    "-o", f"{step1_dir}/{file_name}.nuc_aligned"])
    subprocess.run(start + ["reformat", "-id", step1_dir, "-od", step1_dir, "-rlb"])

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    for f in glob.glob(f"{step1_dir}/*.nuc_aligned"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*Clustal_Omega", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Clustal_Omega {clustalomega_autop_version},pegi3s/clustalomega:{clustalomega_docker_version},'
                     f'Clustal Omega {clustalomega_program_version},"{clustalomega_ref}","{clustalomega_doi}"\n')
            f.write(f',pegi3s/seda:{clustalomega_seda_docker_version},SEDA {clustalomega_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'clustalomega_ref="{clustalomega_ref}"\nclustalomega_doi="{clustalomega_doi}"\n')
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Aligning nucleotide sequences with ClustalOmega", flush=True)
    main()
