#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys

me_tree_autop_version = "4.0.0"
me_tree_megaxcc_docker_version = "10.0.5"
me_tree_megaxcc_program_version = "10.0.5"
megaxcc_ref = "Kumar, S., Stecher, G., Peterson, D., & Tamura, K. (2012)"
megaxcc_doi = "10.1093/bioinformatics/bts507"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global me_tree_autop_version, me_tree_megaxcc_docker_version, me_tree_megaxcc_program_version
    global megaxcc_ref, megaxcc_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "me_tree_bootstrap", "me_tree_treatment",
                          "me_tree_megaxcc_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["me_tree_megaxcc_docker_c_version"]:
        me_tree_autop_version = "?"
        me_tree_megaxcc_docker_version = config["me_tree_megaxcc_docker_c_version"]
        me_tree_megaxcc_program_version = "?"
        megaxcc_ref = "?"
        megaxcc_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-Minimum_Evolution_MEGA_tree_construction"
    mega_out_dir = f"{step1_dir}/mega_me_out"
    os.makedirs(mega_out_dir, exist_ok=True)
    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    with open("/opt/me_tree.mao") as f:
        mao_content = f.read()
    mao_content = mao_content.replace("#bootstrap#", config["me_tree_bootstrap"])
    mao_content = mao_content.replace("#treatment#", config["me_tree_treatment"])
    with open(f"{step1_dir}/me.mao", "w") as f:
        f.write(mao_content)

    shutil.copy(f"/data/{input_dir}/{file_name}", f"{step1_dir}/{file_name}.fas")
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/megax_cc:{me_tree_megaxcc_docker_version}", "megacc",
                    "-a", f"{step1_dir}/me.mao", "-d", f"{step1_dir}/{file_name}.fas", "-o", mega_out_dir],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.copy(f"{mega_out_dir}/{file_name}-1.nwk", f"/data/{out_dir}/{file_name}.nwk")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*me_tree", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'me_tree {me_tree_autop_version},pegi3s/megaxcc:{me_tree_megaxcc_docker_version},'
                     f'MegaX_CC {me_tree_megaxcc_program_version},"{megaxcc_ref}","{megaxcc_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'megaxcc_ref="{megaxcc_ref}"\nmegaxcc_doi="{megaxcc_doi}"\n')


if __name__ == "__main__":
    print("Building a Minimum Evolution tree using MEGA", flush=True)
    main()
