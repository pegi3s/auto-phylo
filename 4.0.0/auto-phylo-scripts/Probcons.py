#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

probcons_autop_version = "4.0.0"
probcons_docker_version = "1.1"
probcons_program_version = "1.1"
probcons_seda_docker_version = "1.7.5-docker29.0.1"
probcons_seda_program_version = "1.7.5"
probcons_ref = "Do CB, Mahabhashyam MS, Brudno M, Batzoglou S. (2005)"
probcons_doi = "10.1101/gr.2821705"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global probcons_autop_version, probcons_docker_version, probcons_program_version
    global probcons_seda_docker_version, probcons_seda_program_version
    global probcons_ref, probcons_doi, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "probcons_docker_c_version", "probcons_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["probcons_docker_c_version"]:
        probcons_autop_version = "?"
        probcons_docker_version = config["probcons_docker_c_version"]
        probcons_program_version = "?"
        probcons_ref = "?"
        probcons_doi = "?"

    if config["probcons_seda_docker_c_version"]:
        probcons_autop_version = "?"
        probcons_seda_docker_version = config["probcons_seda_docker_c_version"]
        probcons_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{probcons_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-PC_sequence_alignment"
    os.makedirs(step1_dir, exist_ok=True)

    # probcons writes the alignment to stdout, so it must be redirected inside the container
    shell_cmd = f"probcons /data/{input_dir}/{file_name} > {step1_dir}/{file_name}.nuc_aligned"
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/probcons_nuc:{probcons_docker_version}", "bash", "-c", shell_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(start + ["reformat", "-id", step1_dir, "-od", step1_dir, "-rlb"])

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    for f in glob.glob(f"{step1_dir}/*.nuc_aligned"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*Probcons", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Probcons {probcons_autop_version},pegi3s/probcons:{probcons_docker_version},'
                     f'Probcons {probcons_program_version},"{probcons_ref}","{probcons_doi}"\n')
            f.write(f',pegi3s/seda:{probcons_seda_docker_version},SEDA {probcons_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'probcons_ref="{probcons_ref}"\nprobcons_doi="{probcons_doi}"\n')
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Aligning nucleotide sequences with Probcons", flush=True)
    main()
