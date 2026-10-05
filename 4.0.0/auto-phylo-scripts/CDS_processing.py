#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

CDS_processing_autop_version = "4.0.0"
CDS_processing_seda_docker_version = "1.7.5-docker29.0.1"
CDS_processing_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global CDS_processing_autop_version, CDS_processing_seda_docker_version
    global CDS_processing_seda_program_version, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "CDS_processing_reformat_headers", "CDS_processing_start_codon",
                          "CDS_processing_max_size_difference", "CDS_processing_reference_file",
                          "CDS_processing_pattern", "CDS_processing_codon_table",
                          "CDS_processing_isoform_min_word_length", "CDS_processing_isoform_ref_size",
                          "CDS_processing_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    reformat_headers = config["CDS_processing_reformat_headers"]
    start_codon = config["CDS_processing_start_codon"]
    max_size_difference = config["CDS_processing_max_size_difference"]
    reference_file = config["CDS_processing_reference_file"]
    pattern = config["CDS_processing_pattern"]
    codon_table = config["CDS_processing_codon_table"]
    isoform_min_word_length = config["CDS_processing_isoform_min_word_length"]
    isoform_ref_size = config["CDS_processing_isoform_ref_size"]
    docker_c_version = config["CDS_processing_seda_docker_c_version"]

    if docker_c_version:
        CDS_processing_autop_version = "?"
        CDS_processing_seda_docker_version = docker_c_version
        CDS_processing_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{CDS_processing_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    if reformat_headers == "y":
        print("Reformatting the sequence headers")
        step1_dir = f"/data/{prefix}1-Reformatted_headers"
        os.makedirs(step1_dir, exist_ok=True)
        subprocess.run(start + ["rename-header-multipart", "-id", f"/data/{input_dir}", "-od", step1_dir,
                                 "-ht", "all", "-fd", " ", "-fm", "keep", "-f", "1"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(start + ["rename-header-replace-word", "-id", step1_dir, "-od", step1_dir,
                                 "-ht", "all", "-tw", "_[0-9]+$", "-r", "-rp", ""],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(start + ["rename-header-replace-word", "-id", step1_dir, "-od", step1_dir,
                                 "-ht", "all", "-tw", r"lcl\|", "-r", "-rp", ""],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(start + ["rename-header-replace-word", "-id", step1_dir, "-od", step1_dir,
                                 "-ht", "all", "-tw", "_cds_", "-r", "-rp", "_"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(start + ["rename-header-replace-word", "-id", step1_dir, "-od", step1_dir,
                                 "-ht", "all", "-tw", r"\.", "-r", "-rp", "_"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(start + ["rename-header-replace-word", "-id", step1_dir, "-od", step1_dir,
                                 "-ht", "all", "-tw", "__", "-r", "-rp", "_"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ambiguous_input_dir = step1_dir
    else:
        print("Keeping the sequence headers")
        step1_dir = f"/data/{prefix}1-Headers_not_reformatted"
        os.makedirs(step1_dir, exist_ok=True)
        for f in glob.glob(f"/data/{input_dir}/*"):
            shutil.copy(f, step1_dir)
        ambiguous_input_dir = step1_dir

    print("Removing sequences with ambiguous nucleotides")
    step2_dir = f"/data/{prefix}2-Remove_ambiguous_nucleotides"
    os.makedirs(step2_dir, exist_ok=True)
    subprocess.run(start + ["pattern-filtering", "-id", ambiguous_input_dir, "-od", step2_dir,
                             "-wop", "[NVHDBMKWSYR]"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Keep sequences with start codons, without in frame stop codons, and that are multiple of 3")
    step3_dir = f"/data/{prefix}3-Start_and_multiple_of_3"
    os.makedirs(step3_dir, exist_ok=True)
    subprocess.run(start + ["filtering", "-id", step2_dir, "-od", step3_dir,
                             "-sc", start_codon, "-rnm3", "-rwifsc"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Removing stop codons")
    step4_dir = f"/data/{prefix}4-Remove_stop_codons"
    os.makedirs(step4_dir, exist_ok=True)
    subprocess.run(start + ["remove-stop-codons", "-id", step3_dir, "-od", step4_dir, "-rlb", "-lb", "unix"],
                   stdout=subprocess.DEVNULL)

    print("Removing sequences by size difference")
    step5_dir = f"/data/{prefix}5-Size_difference"
    os.makedirs(step5_dir, exist_ok=True)
    subprocess.run(start + ["filtering", "-id", step4_dir, "-od", step5_dir, "-rsd",
                             "-maxsd", max_size_difference, "-rsf", f"/data/{reference_file}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Searching for the typical amino acid pattern")
    step6_dir = f"/data/{prefix}6-Search_pattern"
    os.makedirs(step6_dir, exist_ok=True)
    subprocess.run(start + ["pattern-filtering", "-id", step5_dir, "-od", step6_dir, "-wp", pattern,
                             "-caa", "-f", "1", "-ct", codon_table],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Removing Isoforms")
    step7_dir = f"/data/{prefix}7-Remove_isoforms"
    step8_dir = f"/data/{prefix}8-Removed_isoforms"
    os.makedirs(step7_dir, exist_ok=True)
    os.makedirs(step8_dir, exist_ok=True)
    subprocess.run(start + ["remove-isoforms", "-id", step6_dir, "-od", f"{step7_dir}/",
                             "-mwl", isoform_min_word_length, "--reference-size", isoform_ref_size,
                             "-tbm", "longest", "-ifd", step8_dir],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    for f in glob.glob(f"{step7_dir}/*"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*CDS_processing", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'CDS_processing {CDS_processing_autop_version},pegi3s/seda:{CDS_processing_seda_docker_version},'
                     f'SEDA {CDS_processing_seda_program_version},"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    main()

