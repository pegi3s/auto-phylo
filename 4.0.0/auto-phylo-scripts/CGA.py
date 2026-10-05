#!/usr/bin/env python3
import glob
import os
import re
import subprocess
import sys

cga_autop_version = "4.0.0"
cga_seda_docker_version = "1.7.5-docker29.0.1"
cga_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def replace_in_dir(directory, old, new):
    for name in glob.glob(f"{directory}/*"):
        if os.path.isfile(name):
            with open(name) as f:
                content = f.read()
            with open(name, "w") as f:
                f.write(content.replace(old, new))


def main():
    global cga_autop_version, cga_seda_docker_version, cga_seda_program_version, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "cga_reference1", "cga_expect1", "cga_hit_region_window1",
                          "cga_reference2", "cga_expect2", "cga_hit_region_window2", "cga_min_overlap",
                          "cga_reference3", "cga_max_dist", "cga_intron_bp", "cga_min_full_nucleotide_size",
                          "cga_selection_criterion", "cga_selection_correction", "cga_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    docker_c_version = config["cga_seda_docker_c_version"]

    if docker_c_version:
        cga_autop_version = "?"
        cga_seda_docker_version = docker_c_version
        cga_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             "-v", "/var/run/docker.sock:/var/run/docker.sock", "-v", "/tmp:/tmp",
             f"pegi3s/seda:{cga_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    step1a_dir = f"/data/{prefix}1a-blast_results"
    step1b_dir = f"/data/{prefix}1b-blast_results"
    step2_dir = f"/data/{prefix}2-grow_sequences"
    step3_dir = f"/data/{prefix}3-CGA"
    out_path = f"/data/{out_dir}"
    for d in (step1a_dir, step1b_dir, step2_dir, step3_dir, out_path):
        os.makedirs(d, exist_ok=True)

    print("Running CGA-Blast")
    subprocess.run(start + ["blast", "-id", f"/data/{input_dir}", "-od", step1a_dir,
                             "-qf", f"/data/{config['cga_reference1']}", "-qm", "each", "-qbt", "tblastn",
                             "-ev", config["cga_expect1"], "-hit-regions-window", config["cga_hit_region_window1"]],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(start + ["rename-header-multipart", "-id", step1a_dir, "-od", step1a_dir, "-fd", " ", "-f", "1"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(start + ["rename-header-add-word", "-id", step1a_dir, "-od", step1a_dir,
                             "-p", "suffix", "-s", "Seq", "-ai"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if config["cga_reference2"]:
        subprocess.run(start + ["blast", "-id", step1a_dir, "-od", step1b_dir,
                                 "-qf", f"/data/{config['cga_reference2']}", "-qm", "each", "-qbt", "tblastn",
                                 "-ev", config["cga_expect2"], "-hit-regions-window", config["cga_hit_region_window2"]],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        replace_in_dir(step1b_dir, "_", " ")
        subprocess.run(start + ["rename-header-multipart", "-id", step1b_dir, "-od", step1b_dir, "-fd", " ", "-f", "1"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(start + ["rename-header-add-word", "-id", step1b_dir, "-od", step1b_dir,
                                 "-p", "suffix", "-s", "Seq", "-ai"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Running CGA-Growing Sequences")
        subprocess.run(start + ["grow", "-id", step1b_dir, "-od", step2_dir, "-mo", config["cga_min_overlap"]],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("Running CGA-Growing Sequences")
        subprocess.run(start + ["grow", "-id", step1a_dir, "-od", step2_dir, "-mo", config["cga_min_overlap"]],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    replace_in_dir(step2_dir, "_", " ")
    subprocess.run(start + ["rename-header-multipart", "-id", step2_dir, "-od", step2_dir, "-fd", " ", "-f", "1"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(start + ["rename-header-add-word", "-id", step2_dir, "-od", step2_dir,
                             "-p", "suffix", "-s", "Seq", "-ai"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    replace_in_dir(step2_dir, ".", "_")
    subprocess.run(start + ["reformat", "-id", step2_dir, "-od", step2_dir, "-rlb"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Running CGA-CGA")
    subprocess.run(start + ["cga", "-id", step2_dir, "-od", step3_dir, "-rf", f"/data/{config['cga_reference3']}",
                             "-md", config["cga_max_dist"], "-ibp", config["cga_intron_bp"],
                             "-mfs", config["cga_min_full_nucleotide_size"],
                             "-scr", config["cga_selection_criterion"], "-sco", config["cga_selection_correction"]],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(start + ["rename-header-multipart", "-id", step3_dir, "-od", out_path, "-fd", "_", "-f", "1,2,3,4"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*CGA", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'CGA {cga_autop_version},pegi3s/seda:{cga_seda_docker_version},'
                     f'SEDA {cga_seda_program_version},"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    main()

