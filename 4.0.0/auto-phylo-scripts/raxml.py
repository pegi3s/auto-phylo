#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

raxml_autop_version = "4.0.0"
raxml_docker_version = "8.2.13"
raxml_program_version = "8.2.13"
raxml_ref = "Stamatakis A. (2014)"
raxml_doi = "10.1093/bioinformatics/btu033"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global raxml_autop_version, raxml_docker_version, raxml_program_version, raxml_ref, raxml_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "raxml_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["raxml_docker_c_version"]:
        raxml_autop_version = "?"
        raxml_docker_version = config["raxml_docker_c_version"]
        raxml_program_version = "?"
        raxml_ref = "?"
        raxml_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-RAxML"
    out_path = f"/data/{out_dir}"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(out_path, exist_ok=True)

    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data", f"pegi3s/raxml:{raxml_docker_version}",
                    "raxmlHPC", "-m", "GTRGAMMAI", "-p", "12345", "-s", f"/data/{input_dir}/{file_name}",
                    "-n", "raxml_output", "-w", out_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for pattern in ("RAxML_log*", "RAxML_info*", "RAxML_parsimony*", "RAxML_result*"):
        for f in glob.glob(f"{out_path}/{pattern}"):
            shutil.move(f, step1_dir)
    shutil.move(f"{out_path}/RAxML_bestTree.raxml_output", f"{out_path}/RAxML_bestTree.raxml_output.nwk")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*raxml", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'raxml {raxml_autop_version},pegi3s/raxml:{raxml_docker_version},'
                     f'RaxML {raxml_program_version},"{raxml_ref}","{raxml_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'raxml_ref="{raxml_ref}"\nraxml_doi="{raxml_doi}"\n')


if __name__ == "__main__":
    print("Executing RaxML", flush=True)
    main()
