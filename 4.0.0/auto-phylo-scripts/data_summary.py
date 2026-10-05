#!/usr/bin/env python3
import os
import random
import re
import shutil
import subprocess
import sys
import time

data_summary_autop_version = "4.0.0"
data_summary_seda_docker_version = "1.7.5-docker29.0.1"
data_summary_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global data_summary_autop_version, data_summary_seda_docker_version, data_summary_seda_program_version
    global seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "data_summary_taxonomy", "data_summary_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    taxonomy = config["data_summary_taxonomy"]
    docker_c_version = config["data_summary_seda_docker_c_version"]

    if docker_c_version:
        data_summary_autop_version = "?"
        data_summary_seda_docker_version = docker_c_version
        data_summary_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{data_summary_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    step1_dir = f"/data/{prefix}1-Data_summary"
    tmp_dir = f"{step1_dir}/tmp"
    out_tmp_dir = f"/data/{out_dir}/tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(out_tmp_dir, exist_ok=True)

    # -itf takes one flag per taxonomy rank, e.g. "kingdom phylum" -> -itf kingdom -itf phylum
    itf_args = []
    for word in taxonomy.split():
        itf_args += ["-itf", word]

    for name in sorted(os.listdir(f"/data/{input_dir}")):
        shutil.move(f"/data/{input_dir}/{name}", tmp_dir)
        subprocess.run(start + ["rename-ncbi", "-id", tmp_dir, "-od", out_tmp_dir, "-fp", "override",
                                 "-nd", "#"] + itf_args,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.move(f"{tmp_dir}/{name}", f"/data/{input_dir}")
        time.sleep(random.randint(1, 3))

    shutil.rmtree(tmp_dir)

    names = sorted(os.listdir(out_tmp_dir))
    with open(f"{out_tmp_dir}/list", "w") as f:
        f.write("\n".join(names) + ("\n" if names else ""))

    # cut -f2- -d'#': everything after the original filename, still '#'-delimited
    taxonomy_values = sorted(name.split("#", 1)[1] if "#" in name else "" for name in names)
    count_lines = []
    i = 0
    while i < len(taxonomy_values):
        j = i
        while j < len(taxonomy_values) and taxonomy_values[j] == taxonomy_values[i]:
            j += 1
        count_lines.append((j - i, taxonomy_values[i]))
        i = j
    count_lines.sort(key=lambda item: item[1])

    with open(f"/data/{out_dir}/counts", "w") as f:
        for count, value in count_lines:
            f.write(f"{count} {value.replace('#', ' ')}\n")

    species_list = sorted(name.replace("#", "\t") for name in names)
    with open(f"/data/{out_dir}/species_list", "w") as f:
        f.write("\n".join(species_list) + ("\n" if species_list else ""))

    shutil.rmtree(out_tmp_dir)
    for name in os.listdir(f"/data/{out_dir}"):
        src = f"/data/{out_dir}/{name}"
        if os.path.isfile(src):
            shutil.copy(src, step1_dir)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*data_summary", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'data_summary {data_summary_autop_version},pegi3s/seda:{data_summary_seda_docker_version},'
                     f'SEDA {data_summary_seda_program_version},"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Data summary", flush=True)
    main()
