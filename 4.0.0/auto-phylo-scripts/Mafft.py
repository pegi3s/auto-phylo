#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

mafft_autop_version = "4.0.0"
mafft_docker_version = "7.526"
mafft_program_version = "7.526"
mafft_seda_docker_version = "1.7.5-docker29.0.1"
mafft_seda_program_version = "1.7.5"
mafft_ref = "Katoh K, Misawa K, Kuma K, Miyata T. (2002)"
mafft_doi = "10.1093/nar/gkf436"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global mafft_autop_version, mafft_docker_version, mafft_program_version
    global mafft_seda_docker_version, mafft_seda_program_version, mafft_ref, mafft_doi, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "mafft_docker_c_version", "mafft_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["mafft_docker_c_version"]:
        mafft_autop_version = "?"
        mafft_docker_version = config["mafft_docker_c_version"]
        mafft_program_version = "?"
        mafft_ref = "?"
        mafft_doi = "?"

    if config["mafft_seda_docker_c_version"]:
        mafft_autop_version = "?"
        mafft_seda_docker_version = config["mafft_seda_docker_c_version"]
        mafft_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{mafft_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-mafft_sequence_alignment"
    os.makedirs(step1_dir, exist_ok=True)

    # mafft writes the alignment to stdout, so it must be redirected inside the container
    shell_cmd = f"mafft /data/{input_dir}/{file_name} > {step1_dir}/{file_name}.nuc_aligned"
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/mafft:{mafft_docker_version}", "bash", "-c", shell_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(start + ["reformat", "-id", step1_dir, "-od", step1_dir, "-rlb"])

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    for f in glob.glob(f"{step1_dir}/*.nuc_aligned"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*Mafft", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Mafft {mafft_autop_version},pegi3s/mafft:{mafft_docker_version},'
                     f'Mafft {mafft_program_version},"{mafft_ref}","{mafft_doi}"\n')
            f.write(f',pegi3s/seda:{mafft_seda_docker_version},SEDA {mafft_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'mafft_ref="{mafft_ref}"\nmafft_doi="{mafft_doi}"\n')
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Aligning nucleotide sequences with Mafft", flush=True)
    main()
