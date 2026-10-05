#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys

tcoffee_autop_version = "4.0.0"
tcoffee_docker_version = "12.0.7"
tcoffee_program_version = "12.0.7"
tcoffee_ref = "Notredame, C., Higgins, D. G., & Heringa, J. (2000)"
tcoffee_doi = "10.1006/jmbi.2000.4042"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global tcoffee_autop_version, tcoffee_docker_version, tcoffee_program_version, tcoffee_ref, tcoffee_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "tcoffee_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["tcoffee_docker_c_version"]:
        tcoffee_autop_version = "?"
        tcoffee_docker_version = config["tcoffee_docker_c_version"]
        tcoffee_program_version = "?"
        tcoffee_ref = "?"
        tcoffee_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    print("Aligning sequences with T-coffee")
    step1_dir = f"/data/{prefix}1-T-coffee_sequence_alignment_Clustal"
    os.makedirs(step1_dir, exist_ok=True)
    # NOTE: mirrors the original script, which omits the image tag for this call
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data", "pegi3s/tcoffee", "t_coffee",
                    f"/data/{input_dir}/{file_name}", "-run_name", f"{step1_dir}/{file_name}.aln"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Converting to FASTA")
    step2_dir = f"/data/{prefix}2-T-coffee_FASTA_Conversion"
    os.makedirs(step2_dir, exist_ok=True)
    aligned_path = f"{step2_dir}/{file_name}.aligned"
    open(aligned_path, "w").close()
    nuc_aligned_path = f"{step2_dir}/{file_name}.nuc_aligned"
    with open(nuc_aligned_path, "w") as out:
        subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                        f"pegi3s/tcoffee:{tcoffee_docker_version}", "t_coffee", "-other_pg", "seq_reformat",
                        "-in", f"{step1_dir}/{file_name}.aln", "-output", "fasta"], stdout=out)

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    shutil.copy(nuc_aligned_path, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*T-coffee", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'T-coffee {tcoffee_autop_version},pegi3s/tcoffee:{tcoffee_docker_version},'
                     f'T-Coffee {tcoffee_program_version},"{tcoffee_ref}","{tcoffee_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'tcoffee_ref="{tcoffee_ref}"\ntcoffee_doi="{tcoffee_doi}"\n')


if __name__ == "__main__":
    main()
