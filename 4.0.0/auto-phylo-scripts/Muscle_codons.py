#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

muscle_codons_autop_version = "4.0.0"
muscle_codons_docker_version = "5.3"
muscle_codons_program_version = "5.3"
muscle_codons_emboss_docker_version = "6.6.0"
muscle_codons_emboss_program_version = "6.6.0"
muscle_codons_translatorx_docker_version = "01.09.2022"
muscle_codons_translatorx_program_version = "https://translatorx.org"
muscle_ref = "Edgar RC. (2004)"
muscle_doi = "10.1093/nar/gkh340"
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
    global muscle_codons_autop_version, muscle_codons_docker_version, muscle_codons_program_version
    global muscle_codons_emboss_docker_version, muscle_codons_emboss_program_version
    global muscle_codons_translatorx_docker_version, muscle_codons_translatorx_program_version
    global muscle_ref, muscle_doi, emboss_ref, emboss_doi, translatorx_ref, translatorx_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "muscle_codons_docker_c_version", "muscle_codons_emboss_docker_c_version",
                          "muscle_codons_translatorx_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["muscle_codons_docker_c_version"]:
        muscle_codons_autop_version = "?"
        muscle_codons_docker_version = config["muscle_codons_docker_c_version"]
        muscle_codons_program_version = "?"
        muscle_ref = "?"
        muscle_doi = "?"

    if config["muscle_codons_emboss_docker_c_version"]:
        muscle_codons_autop_version = "?"
        muscle_codons_emboss_docker_version = config["muscle_codons_emboss_docker_c_version"]
        muscle_codons_emboss_program_version = "?"
        emboss_ref = "?"
        emboss_doi = "?"

    if config["muscle_codons_translatorx_docker_c_version"]:
        muscle_codons_autop_version = "?"
        muscle_codons_translatorx_docker_version = config["muscle_codons_translatorx_docker_c_version"]
        muscle_codons_translatorx_program_version = "?"
        translatorx_ref = "?"
        translatorx_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-MUSCLE_Translated_sequences"
    os.makedirs(step1_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/emboss:{muscle_codons_emboss_docker_version}", "transeq",
                    "-sequence", f"/data/{input_dir}/{file_name}", "-outseq", f"{step1_dir}/{file_name}.pep"])
    pep_path = f"{step1_dir}/{file_name}.pep"
    with open(pep_path) as f:
        content = f.read()
    with open(pep_path, "w") as f:
        f.write(re.sub(r"_1$", "", content, flags=re.MULTILINE))

    print("Aligning amino acid sequences with MUSCLE")
    step2_dir = f"/data/{prefix}2-MUSCLE_AA_sequence_alignment"
    os.makedirs(step2_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/muscle:{muscle_codons_docker_version}", "-align", pep_path,
                    "-output", f"{step2_dir}/{file_name}.pep_aligned"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Creating a nucleotide alignment using the amino acid alignment as a guide")
    step3_dir = f"/data/{prefix}3-MUSCLE_Nuc_sequence_alignment"
    os.makedirs(step3_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/translatorx:{muscle_codons_translatorx_docker_version}",
                    "translatorx_vLocal.pl", "-i", f"/data/{input_dir}/{file_name}",
                    "-a", f"{step2_dir}/{file_name}.pep_aligned", "-o", f"{step3_dir}/{file_name}.nuc_aligned"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.move(f"{step3_dir}/{file_name}.nuc_aligned.nt_ali.fasta", f"{step3_dir}/{file_name}.nuc_aligned")
    for f in glob.glob(f"{step3_dir}/{file_name}*ali.fasta"):
        os.remove(f)

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    for f in glob.glob(f"{step3_dir}/*.nuc_aligned"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*Muscle_codons", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Muscle_codons {muscle_codons_autop_version},pegi3s/muscle:{muscle_codons_docker_version},'
                     f'Muscle {muscle_codons_program_version},"{muscle_ref}","{muscle_doi}"\n')
            f.write(f',pegi3s/emboss:{muscle_codons_emboss_docker_version},'
                    f'EMBOSS {muscle_codons_emboss_program_version},"{emboss_ref}","{emboss_doi}"\n')
            f.write(f',pegi3s/translatorx ({muscle_codons_translatorx_docker_version}),'
                    f'Translator X ({muscle_codons_translatorx_program_version}),'
                    f'"{translatorx_ref}","{translatorx_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'muscle_ref="{muscle_ref}"\nmuscle_doi="{muscle_doi}"\n')
        f.write(f'emboss_ref="{emboss_ref}"\nemboss_doi="{emboss_doi}"\n')
        # NOTE: mirrors a pre-existing bug in the original script (writes translatorx_ref twice instead of the doi)
        f.write(f'translatorx_ref="{translatorx_ref}"\ntranslatorx_ref="{translatorx_ref}"\n')


if __name__ == "__main__":
    main()
