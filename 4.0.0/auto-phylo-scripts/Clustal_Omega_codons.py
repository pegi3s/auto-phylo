#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

clustalomega_codons_autop_version = "4.0.0"
clustalomega_codons_docker_version = "1.2.4"
clustalomega_codons_program_version = "1.2.4"
clustalomega_codons_emboss_docker_version = "6.6.0"
clustalomega_codons_emboss_program_version = "6.6.0"
clustalomega_codons_translatorx_docker_version = "01.09.2022"
clustalomega_codons_translatorx_program_version = "https://translatorx.org"
clustalomega_ref = "Sievers, F., & Higgins, D. G. (2014)"
clustalomega_doi = "10.1002/0471250953.bi0313s48"
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
    global clustalomega_codons_autop_version, clustalomega_codons_docker_version, clustalomega_codons_program_version
    global clustalomega_codons_emboss_docker_version, clustalomega_codons_emboss_program_version
    global clustalomega_codons_translatorx_docker_version, clustalomega_codons_translatorx_program_version
    global clustalomega_ref, clustalomega_doi, emboss_ref, emboss_doi, translatorx_ref, translatorx_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "clustalomega_codons_docker_c_version",
                          "clustalomega_codons_emboss_docker_c_version",
                          "clustalomega_codons_translatorx_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["clustalomega_codons_docker_c_version"]:
        clustalomega_codons_autop_version = "?"
        clustalomega_codons_docker_version = config["clustalomega_codons_docker_c_version"]
        clustalomega_codons_program_version = "?"
        clustalomega_ref = "?"
        clustalomega_doi = "?"

    if config["clustalomega_codons_emboss_docker_c_version"]:
        clustalomega_codons_autop_version = "?"
        clustalomega_codons_emboss_docker_version = config["clustalomega_codons_emboss_docker_c_version"]
        clustalomega_codons_emboss_program_version = "?"
        emboss_ref = "?"
        emboss_doi = "?"

    if config["clustalomega_codons_translatorx_docker_c_version"]:
        clustalomega_codons_autop_version = "?"
        clustalomega_codons_translatorx_docker_version = config["clustalomega_codons_translatorx_docker_c_version"]
        clustalomega_codons_translatorx_program_version = "?"
        translatorx_ref = "?"
        translatorx_doi = "?"

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-COAA_Translated_sequences"
    os.makedirs(step1_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/emboss:{clustalomega_codons_emboss_docker_version}", "transeq",
                    "-sequence", f"/data/{input_dir}/{file_name}",
                    "-outseq", f"{step1_dir}/{file_name}.pep"])
    pep_path = f"{step1_dir}/{file_name}.pep"
    with open(pep_path) as f:
        content = f.read()
    with open(pep_path, "w") as f:
        f.write(re.sub(r"_1$", "", content, flags=re.MULTILINE))

    print("Aligning amino acid sequences with ClustalOmega")
    step2_dir = f"/data/{prefix}2-COAA_AA_sequence_alignment"
    os.makedirs(step2_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/clustalomega:{clustalomega_codons_docker_version}",
                    "-i", pep_path, "-o", f"{step2_dir}/{file_name}.pep_aligned"])

    print("Creating a nucleotide alignment using the amino acid alignment as a guide")
    step3_dir = f"/data/{prefix}3-COAA_Nuc_sequence_alignment"
    os.makedirs(step3_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/translatorx:{clustalomega_codons_translatorx_docker_version}",
                    "translatorx_vLocal.pl", "-i", f"/data/{input_dir}/{file_name}",
                    "-a", f"{step2_dir}/{file_name}.pep_aligned",
                    "-o", f"{step3_dir}/{file_name}.nuc_aligned"],
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
    if not re.search(r"^\s*Clustal_Omega_codons", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Clustal_Omega_codons {clustalomega_codons_autop_version},'
                     f'pegi3s/clustalomega:{clustalomega_codons_docker_version},'
                     f'Clustal Omega {clustalomega_codons_program_version},"{clustalomega_ref}","{clustalomega_doi}"\n')
            f.write(f',pegi3s/emboss:{clustalomega_codons_emboss_docker_version},'
                    f'EMBOSS {clustalomega_codons_emboss_program_version},"{emboss_ref}","{emboss_doi}"\n')
            f.write(f',pegi3s/translatorx ({clustalomega_codons_translatorx_docker_version}),'
                    f'Translator X ({clustalomega_codons_translatorx_program_version}),'
                    f'"{translatorx_ref}","{translatorx_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'clustalomega_ref="{clustalomega_ref}"\nclustalomega_doi="{clustalomega_doi}"\n')
        f.write(f'emboss_ref="{emboss_ref}"\nemboss_doi="{emboss_doi}"\n')
        f.write(f'translatorx_ref="{translatorx_ref}"\ntranslatorx_doi="{translatorx_doi}"\n')


if __name__ == "__main__":
    main()
