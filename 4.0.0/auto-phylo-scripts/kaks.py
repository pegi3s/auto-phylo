#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

kaks_autop_version = "4.0.0"
kaks_docker_version = "2.0"
kaks_program_version = "2.0"
kaks_seda_docker_version = "1.7.5-docker29.0.1"
kaks_seda_program_version = "1.7.5"
kaks_ref = "Wang D, Zhang Y, Zhang Z, Zhu J, Yu J. (2010)"
kaks_doi = "10.1016/S1672-0229(10)60008-3"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global kaks_autop_version, kaks_docker_version, kaks_program_version
    global kaks_seda_docker_version, kaks_seda_program_version, kaks_ref, kaks_doi, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "kaks_model", "kaks_genetic_code",
                          "kaks_docker_c_version", "kaks_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    model = config["kaks_model"]
    genetic_code = config["kaks_genetic_code"]

    if config["kaks_docker_c_version"]:
        kaks_autop_version = "?"
        kaks_docker_version = config["kaks_docker_c_version"]
        kaks_program_version = "?"
        kaks_ref = "?"
        kaks_doi = "?"

    if config["kaks_seda_docker_c_version"]:
        kaks_autop_version = "?"
        kaks_seda_docker_version = config["kaks_seda_docker_c_version"]
        kaks_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             "-v", "/var/run/docker.sock:/var/run/docker.sock", "-v", "/tmp:/tmp",
             f"pegi3s/seda:{kaks_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    out_path = f"/data/{out_dir}"
    step1_dir = f"/data/{prefix}1-KaKs"
    os.makedirs(out_path, exist_ok=True)
    os.makedirs(step1_dir, exist_ok=True)

    input_path = f"/data/{input_dir}"
    file_name = os.listdir(input_path)[0]
    subprocess.run(start + ["reformat", "-id", input_path, "-od", input_path, "-rlb"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    shell_cmd = (f"FASTA-AXT /data/{file_name} && KaKs_Calculator -i /data/{file_name}.axt "
                 f"-o /data/{file_name}.axt.kaks -m {model} -c {genetic_code}")
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}/{input_dir}:/data",
                    f"pegi3s/kakscalculator:{kaks_docker_version}", "bash", "-c", shell_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in glob.glob(f"{input_path}/*.axt"):
        shutil.copy(f, step1_dir)
    for f in glob.glob(f"{input_path}/*.kaks"):
        shutil.copy(f, out_path)
    for f in glob.glob(f"{input_path}/*.axt") + glob.glob(f"{input_path}/*.kaks"):
        os.remove(f)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*kaks", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'kaks {kaks_autop_version},pegi3s/kakscalculator:{kaks_docker_version},'
                     f'KaKs Calculator {kaks_program_version},"{kaks_ref}","{kaks_doi}"\n')
            f.write(f',pegi3s/seda:{kaks_seda_docker_version},SEDA {kaks_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'kaks_ref="{kaks_ref}"\nkaks_doi="{kaks_doi}"\n')
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("KaKs Calculator", flush=True)
    main()

