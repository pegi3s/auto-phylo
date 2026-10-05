#!/usr/bin/env python3
import os
import random
import re
import shutil
import subprocess
import sys
import time

add_taxonomy_autop_version = "4.0.0"
add_taxonomy_seda_docker_version = "1.7.5-docker29.0.1"
add_taxonomy_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global add_taxonomy_autop_version, add_taxonomy_seda_docker_version, add_taxonomy_seda_program_version
    global seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "add_tax_taxonomy_header", "add_taxonomy_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    taxonomy_header = config["add_tax_taxonomy_header"]
    docker_c_version = config["add_taxonomy_seda_docker_c_version"]

    if docker_c_version:
        add_taxonomy_autop_version = "?"
        add_taxonomy_seda_docker_version = docker_c_version
        add_taxonomy_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{add_taxonomy_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    step1_dir = f"/data/{prefix}1-Add_taxonomy"
    tmp_dir = f"{step1_dir}/tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(f"/data/{out_dir}", exist_ok=True)

    # -itf takes one flag per taxonomy rank, e.g. "kingdom phylum" -> -itf kingdom -itf phylum
    itf_args = []
    for word in taxonomy_header.split():
        itf_args += ["-itf", word]

    for name in sorted(os.listdir(f"/data/{input_dir}")):
        shutil.move(f"/data/{input_dir}/{name}", tmp_dir)
        subprocess.run(start + ["rename-ncbi", "-id", tmp_dir, "-od", f"/data/{out_dir}", "-hp", "prefix",
                                 "-hd", "_", "-rbs", "-rsc", "-r", "_", "-nd", "_"] + itf_args,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.move(f"{tmp_dir}/{name}", f"/data/{input_dir}")
        time.sleep(random.randint(1, 3))

    subprocess.run(start + ["rename-header-replace-interval", "-id", f"/data/{out_dir}", "-od", f"/data/{out_dir}",
                             "-ht", "all", "-fr", "(", "-to", ")", "-ir", ""])
    subprocess.run(start + ["rename-header-replace-word", "-id", f"/data/{out_dir}", "-od", f"/data/{out_dir}",
                             "-ht", "all", "-tw", r"\.", "-r", "-rp", "_"])
    subprocess.run(start + ["rename-header-replace-word", "-id", f"/data/{out_dir}", "-od", f"/data/{out_dir}",
                             "-ht", "all", "-tw", "__", "-r", "-rp", "_"])
    os.rmdir(tmp_dir)

    original_list = sorted(os.listdir(f"/data/{input_dir}"))
    final_list = sorted(os.listdir(f"/data/{out_dir}"))
    with open(f"{step1_dir}/original_list", "w") as f:
        f.write("\n".join(original_list) + ("\n" if original_list else ""))
    with open(f"{step1_dir}/final_list", "w") as f:
        f.write("\n".join(final_list) + ("\n" if final_list else ""))

    # names present in both the input and the output are ones rename-ncbi failed to process
    unprocessed = sorted(set(original_list) & set(final_list))
    with open(f"{step1_dir}/unprocessed_list", "w") as f:
        f.write("\n".join(unprocessed) + ("\n" if unprocessed else ""))

    failed_dir = f"/data/{prefix}2-Files_that_failed"
    os.makedirs(failed_dir, exist_ok=True)
    for name in unprocessed:
        shutil.copy(f"/data/{input_dir}/{name}", failed_dir)
        os.remove(f"/data/{out_dir}/{name}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*add_taxonomy", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'add_taxonomy {add_taxonomy_autop_version},pegi3s/seda:{add_taxonomy_seda_docker_version},'
                     f'SEDA {add_taxonomy_seda_program_version},"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Adding taxonomy information", flush=True)
    main()

