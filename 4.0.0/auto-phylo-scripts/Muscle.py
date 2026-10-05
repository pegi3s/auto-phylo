#!/usr/bin/env python3
import os
import re
import subprocess
import sys

muscle_autop_version = "4.0.0"
muscle_docker_version = "5.3"
muscle_program_version = "5.3"
muscle_seda_docker_version = "1.7.5-docker29.0.1"
muscle_seda_program_version = "1.7.5"
muscle_ref = "Edgar RC. (2004)"
muscle_doi = "10.1093/nar/gkh340"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global muscle_autop_version, muscle_docker_version, muscle_program_version
    global muscle_seda_docker_version, muscle_seda_program_version, muscle_ref, muscle_doi, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "muscle_docker_c_version", "muscle_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["muscle_docker_c_version"]:
        muscle_autop_version = "?"
        muscle_docker_version = config["muscle_docker_c_version"]
        muscle_program_version = "?"
        muscle_ref = "?"
        muscle_doi = "?"

    if config["muscle_seda_docker_c_version"]:
        muscle_autop_version = "?"
        muscle_seda_docker_version = config["muscle_seda_docker_c_version"]
        muscle_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{muscle_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    file_name = os.listdir(f"/data/{input_dir}")[0]

    out_path = f"/data/{out_dir}"
    os.makedirs(out_path, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data", f"pegi3s/muscle:{muscle_docker_version}",
                    "-align", f"/data/{input_dir}/{file_name}", "-output", f"{out_path}/{file_name}.nuc_aligned"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(start + ["reformat", "-id", out_path, "-od", out_path, "-rlb"])

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*Muscle", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Muscle {muscle_autop_version},pegi3s/muscle:{muscle_docker_version},'
                     f'Muscle {muscle_program_version},,\n')
            f.write(f',pegi3s/seda:{muscle_seda_docker_version},SEDA {muscle_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'muscle_ref="{muscle_ref}"\nmuscle_doi="{muscle_doi}"\n')
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Aligning nucleotide sequences with MUSCLE", flush=True)
    main()
