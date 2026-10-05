#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

tcoffee_codons_autop_version = "4.0.0"
tcoffee_codons_docker_version = "12.0.7"
tcoffee_codons_program_version = "12.0.7"
tcoffee_codons_emboss_docker_version = "6.6.0"
tcoffee_codons_emboss_program_version = "6.6.0"
tcoffee_codons_translatorx_docker_version = "01.09.2022"
tcoffee_codons_translatorx_program_version = "https://translatorx.org"
tcoffee_ref = "Notredame, C., Higgins, D. G., & Heringa, J. (2000)"
tcoffee_doi = "10.1006/jmbi.2000.4042"
emboss_ref = "Rice, P., Longden, I., & Bleasby, A. (2000)"
emboss_doi = "10.1016/s0168-9525(00)02024-2"
translatorx_ref = "Abascal, F., Zardoya, R., & Telford, M. J. (2010)"
translatorx_doi = "10.1093/nar/gkq291"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global tcoffee_codons_autop_version, tcoffee_codons_docker_version, tcoffee_codons_program_version
    global tcoffee_codons_emboss_docker_version, tcoffee_codons_emboss_program_version
    global tcoffee_codons_translatorx_docker_version, tcoffee_codons_translatorx_program_version
    global tcoffee_ref, tcoffee_doi, emboss_ref, emboss_doi, translatorx_ref, translatorx_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "tcoffee_codons_docker_c_version",
                          "tcoffee_codons_emboss_docker_c_version", "tcoffee_codons_translatorx_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["tcoffee_codons_docker_c_version"]:
        tcoffee_codons_autop_version = "?"
        tcoffee_codons_docker_version = config["tcoffee_codons_docker_c_version"]
        tcoffee_codons_program_version = "?"
        tcoffee_ref = "?"
        tcoffee_doi = "?"

    if config["tcoffee_codons_emboss_docker_c_version"]:
        tcoffee_codons_autop_version = "?"
        tcoffee_codons_emboss_docker_version = config["tcoffee_codons_emboss_docker_c_version"]
        tcoffee_codons_emboss_program_version = "?"
        emboss_ref = "?"
        emboss_doi = "?"

    if config["tcoffee_codons_translatorx_docker_c_version"]:
        tcoffee_codons_autop_version = "?"
        tcoffee_codons_translatorx_docker_version = config["tcoffee_codons_translatorx_docker_c_version"]
        tcoffee_codons_translatorx_program_version = "?"
        translatorx_ref = "?"
        translatorx_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-T-coffee_AA_Translated_sequences"
    os.makedirs(step1_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/emboss:{tcoffee_codons_emboss_docker_version}", "transeq",
                    "-sequence", f"/data/{input_dir}/{file_name}", "-outseq", f"{step1_dir}/{file_name}.pep"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pep_path = f"{step1_dir}/{file_name}.pep"
    with open(pep_path) as f:
        content = f.read()
    with open(pep_path, "w") as f:
        f.write(re.sub(r"_1$", "", content, flags=re.MULTILINE))

    print("Aligning amino acid sequences with T-coffee")
    step2_dir = f"/data/{prefix}2-T-coffee_AA_AA_sequence_alignment_Clustal"
    os.makedirs(step2_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/tcoffee:{tcoffee_codons_docker_version}", "t_coffee", pep_path,
                    "-run_name", f"{step2_dir}/{file_name}.aln"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Converting to FASTA")
    step3_dir = f"/data/{prefix}3-T-coffee_AA_convert_to_FASTA"
    os.makedirs(step3_dir, exist_ok=True)
    pep_aligned_path = f"{step3_dir}/{file_name}.pep_aligned"
    open(pep_aligned_path, "w").close()
    with open(pep_aligned_path, "w") as out:
        subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                        f"pegi3s/tcoffee:{tcoffee_codons_docker_version}", "t_coffee", "-other_pg", "seq_reformat",
                        "-in", f"{step2_dir}/{file_name}.aln", "-output", "fasta"], stdout=out)

    print("Creating a nucleotide alignment using the amino acid alignment as a guide")
    step4_dir = f"/data/{prefix}4-T-coffee_AA_Nuc_sequence_alignment"
    os.makedirs(step4_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/translatorx:{tcoffee_codons_translatorx_docker_version}",
                    "translatorx_vLocal.pl", "-i", f"/data/{input_dir}/{file_name}",
                    "-a", pep_aligned_path, "-o", f"{step4_dir}/{file_name}.nuc_aligned"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.move(f"{step4_dir}/{file_name}.nuc_aligned.nt_ali.fasta", f"{step4_dir}/{file_name}.nuc_aligned")
    for f in glob.glob(f"{step4_dir}/{file_name}*ali.fasta"):
        os.remove(f)

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    for f in glob.glob(f"{step4_dir}/*.nuc_aligned"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*T-coffee_codons", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'T-coffee_codons {tcoffee_codons_autop_version},pegi3s/tcoffee:{tcoffee_codons_docker_version},'
                     f'T-coffee {tcoffee_codons_program_version},"{tcoffee_ref}","{tcoffee_doi}"\n')
            f.write(f',pegi3s/emboss:{tcoffee_codons_emboss_docker_version},'
                    f'EMBOSS {tcoffee_codons_emboss_program_version},"{emboss_ref}","{emboss_doi}"\n')
            f.write(f',pegi3s/translatorx ({tcoffee_codons_translatorx_docker_version}),'
                    f'Translator X ({tcoffee_codons_translatorx_program_version}),'
                    f'"{translatorx_ref}","{translatorx_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'tcoffee_ref="{tcoffee_ref}"\ntcoffee_doi="{tcoffee_doi}"\n')
        f.write(f'emboss_ref="{emboss_ref}"\nemboss_doi="{emboss_doi}"\n')
        f.write(f'translatorx_ref="{translatorx_ref}"\ntranslatorx_doi="{translatorx_doi}"\n')


if __name__ == "__main__":
    main()
