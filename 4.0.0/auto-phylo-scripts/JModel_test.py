#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

jmodeltest_autop_version = "4.0.0"
jmodeltest_docker_version = "2.1.10"
jmodeltest_program_version = "2.1.10"
jmodeltest_seda_docker_version = "1.7.5-docker29.0.1"
jmodeltest_seda_program_version = "1.7.5"
jmodeltest_ref = "Darriba, D., Taboada, G. L., Doallo, R., & Posada, D. (2012)"
jmodeltest_doi = "10.1038/nmeth.2109"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global jmodeltest_autop_version, jmodeltest_docker_version, jmodeltest_program_version
    global jmodeltest_seda_docker_version, jmodeltest_seda_program_version
    global jmodeltest_ref, jmodeltest_doi, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "jmodeltest_docker_c_version", "jmodeltest_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["jmodeltest_docker_c_version"]:
        jmodeltest_autop_version = "?"
        jmodeltest_docker_version = config["jmodeltest_docker_c_version"]
        jmodeltest_program_version = "?"
        jmodeltest_ref = "?"
        jmodeltest_doi = "?"

    if config["jmodeltest_seda_docker_c_version"]:
        jmodeltest_autop_version = "?"
        jmodeltest_seda_docker_version = config["jmodeltest_seda_docker_c_version"]
        jmodeltest_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{jmodeltest_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-Header_rename"
    step2_dir = f"/data/{prefix}2-J-model_test"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(step2_dir, exist_ok=True)
    os.makedirs(f"/data/{out_dir}", exist_ok=True)

    subprocess.run(start + ["rename-header-replace-word", "-id", f"/data/{input_dir}", "-od", step1_dir,
                             "-ht", "all", "-tw", "[^0-9,a-z,A-Z]", "-r", "-rp", "_"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/jmodeltest2:{jmodeltest_docker_version}", "java", "-jar",
                    "/jmodeltest2/dist/jModelTest.jar", "-d", f"{step1_dir}/{file_name}", "-g", "4", "-i", "-f",
                    "-AIC", "-BIC", "-a", "-o", f"{step2_dir}/{file_name}.AIC"])
    for f in glob.glob(f"{step2_dir}/*"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*JModel_test", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'JModel_test {jmodeltest_autop_version},pegi3s/jmodeltest2:{jmodeltest_docker_version},'
                     f'JModel Test {jmodeltest_program_version},"{jmodeltest_ref}","{jmodeltest_doi}"\n')
            f.write(f',pegi3s/seda:{jmodeltest_seda_docker_version},SEDA {jmodeltest_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'jmodeltest_ref="{jmodeltest_ref}"\njmodeltest_doi="{jmodeltest_doi}"\n')
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Running J-model test", flush=True)
    main()
