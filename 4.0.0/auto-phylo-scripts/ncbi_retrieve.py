#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

ncbi_retrieve_autop_version = "4.0.0"
ncbi_retrieve_docker_version = "1.0.1-docker29.0.1"
ncbi_retrieve_program_version = "1.0.1"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global ncbi_retrieve_autop_version, ncbi_retrieve_docker_version, ncbi_retrieve_program_version

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "include", "database_type", "ncbi_retrieve_docker_c_version")
    data_dir = config["dir"]
    include = config["include"]
    database_type = config["database_type"]

    if config["ncbi_retrieve_docker_c_version"]:
        ncbi_retrieve_autop_version = "?"
        ncbi_retrieve_docker_version = config["ncbi_retrieve_docker_c_version"]
        ncbi_retrieve_program_version = "?"

    out_path = f"/data/{out_dir}"
    step1_dir = f"/data/{prefix}1-accessions"
    os.makedirs(out_path, exist_ok=True)
    os.makedirs(step1_dir, exist_ok=True)

    host_input_dir = f"{data_dir}/{input_dir}"
    cmd = ["docker", "run", "--rm", "-v", f"{host_input_dir}:/data",
           "-v", "/var/run/docker.sock:/var/run/docker.sock",
           f"pegi3s/ncbi_retrieve:{ncbi_retrieve_docker_version}", "-db", database_type]
    if include:
        cmd += ["-inc", include]
    cmd += ["-path", host_input_dir]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    input_path = f"/data/{input_dir}"
    log_file = f"{input_path}/intermediate/log_file.txt"
    if os.path.exists(log_file):
        shutil.move(log_file, step1_dir)

    retrieve_out_dir = f"{input_path}/out_dir"
    for root, _dirs, files in os.walk(retrieve_out_dir):
        for name in files:
            path = os.path.join(root, name)
            if os.path.getsize(path) == 0:
                os.remove(path)

    for f in glob.glob(f"{retrieve_out_dir}/*"):
        shutil.move(f, out_path)

    shutil.rmtree(f"{input_path}/intermediate", ignore_errors=True)
    shutil.rmtree(retrieve_out_dir, ignore_errors=True)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*ncbi_retrieve", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'ncbi_retrieve {ncbi_retrieve_autop_version},pegi3s/ncbi_retrieve:{ncbi_retrieve_docker_version},'
                     f'ncbi_retrieve {ncbi_retrieve_program_version},,\n')


if __name__ == "__main__":
    print("Retrieving files", flush=True)
    main()
