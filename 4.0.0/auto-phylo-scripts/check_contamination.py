#!/usr/bin/env python3
import os
import random
import re
import shutil
import subprocess
import sys
import time

check_contamination_autop_version = "4.0.0"
check_contamination_seda_docker_version = "1.7.5-docker29.0.1"
check_contamination_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global check_contamination_autop_version, check_contamination_seda_docker_version
    global check_contamination_seda_program_version, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "check_cont_input_delete", "check_cont_intermediate_delete",
                          "check_cont_taxonomy", "check_cont_category", "check_contamination_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    input_delete = config["check_cont_input_delete"] or "no"
    intermediate_delete = config["check_cont_intermediate_delete"] or "no"
    taxonomy = config["check_cont_taxonomy"]
    category = config["check_cont_category"]
    docker_c_version = config["check_contamination_seda_docker_c_version"]

    if docker_c_version:
        check_contamination_autop_version = "?"
        check_contamination_seda_docker_version = docker_c_version
        check_contamination_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{check_contamination_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    step1_dir = f"/data/{prefix}1-Contamination_check"
    tmp_dir = f"{step1_dir}/tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    for name in sorted(os.listdir(f"/data/{input_dir}")):
        shutil.move(f"/data/{input_dir}/{name}", tmp_dir)
        subprocess.run(start + ["rename-ncbi", "-id", tmp_dir, "-od", step1_dir, "-fp", "suffix", "-fd", "_",
                                 "-hp", "none", "-rbs", "-rsc", "-r", "_", "-nd", "#", "-itf"] + taxonomy.split(),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if input_delete == "yes":
            open(f"{tmp_dir}/{name}", "w").close()
        shutil.move(f"{tmp_dir}/{name}", f"/data/{input_dir}")
        time.sleep(random.randint(1, 3))

    shutil.rmtree(tmp_dir)

    out_path = f"/data/{out_dir}"
    step2_dir = f"/data/{prefix}2-Not_contaminated"
    step3_dir = f"/data/{prefix}3-Control_lists"
    step4_dir = f"/data/{prefix}4-Suspicious_Files"
    for d in (out_path, step2_dir, step3_dir, step4_dir):
        os.makedirs(d, exist_ok=True)

    original_list = sorted(os.listdir(step1_dir))
    # files renamed with the expected taxonomy category suffix are considered clean
    filtered_list = sorted(n for n in original_list if n.endswith(f"#{category}"))
    with open(f"{step3_dir}/original_list", "w") as f:
        f.write("\n".join(original_list) + ("\n" if original_list else ""))
    with open(f"{step3_dir}/filtered_list", "w") as f:
        f.write("\n".join(filtered_list) + ("\n" if filtered_list else ""))

    suspicious_list = sorted(set(original_list) - set(filtered_list))
    with open(f"{step3_dir}/suspicious_list", "w") as f:
        f.write("\n".join(suspicious_list) + ("\n" if suspicious_list else ""))

    for name in suspicious_list:
        shutil.copy(f"{step1_dir}/{name}", step4_dir)
    for name in filtered_list:
        shutil.copy(f"{step1_dir}/{name}", out_path)

    if intermediate_delete != "yes":
        for name in filtered_list:
            shutil.copy(f"{step1_dir}/{name}", step2_dir)
    else:
        for name in original_list:
            os.remove(f"{step1_dir}/{name}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*check_contamination", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'check_contamination {check_contamination_autop_version},'
                     f'pegi3s/seda:{check_contamination_seda_docker_version},'
                     f'SEDA {check_contamination_seda_program_version},"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Check for unwanted genomes", flush=True)
    main()

