#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

probcons_refinement_autop_version = "4.0.0"
probcons_refinement_docker_version = "1.1"
probcons_refinement_program_version = "1.1"
probcons_ref = "Do CB, Mahabhashyam MS, Brudno M, Batzoglou S. (2005)"
probcons_doi = "10.1101/gr.2821705"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global probcons_refinement_autop_version, probcons_refinement_docker_version
    global probcons_refinement_program_version, probcons_ref, probcons_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "probcons_refin_iterations", "probcons_refinement_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    iterations = config["probcons_refin_iterations"]

    if config["probcons_refinement_docker_c_version"]:
        probcons_refinement_autop_version = "?"
        probcons_refinement_docker_version = config["probcons_refinement_docker_c_version"]
        probcons_refinement_program_version = "?"
        probcons_ref = "?"
        probcons_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-Probcons_sequence_refinement"
    os.makedirs(step1_dir, exist_ok=True)

    shell_cmd = (f"probcons -ir {iterations} /data/{input_dir}/{file_name} > "
                 f"{step1_dir}/{file_name}.refined.nuc_aligned")
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/probcons_nuc:{probcons_refinement_docker_version}", "bash", "-c", shell_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    for f in glob.glob(f"{step1_dir}/*.nuc_aligned"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*Probcons_refinement", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Probcons_refinement {probcons_refinement_autop_version},'
                     f'pegi3s/probcons:{probcons_refinement_docker_version},'
                     f'Probcons {probcons_refinement_program_version},"{probcons_ref}","{probcons_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'probcons_ref="{probcons_ref}"\nprobcons_doi="{probcons_doi}"\n')


if __name__ == "__main__":
    print("Refining sequences with Probcons", flush=True)
    main()
