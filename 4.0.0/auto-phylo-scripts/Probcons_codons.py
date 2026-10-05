#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

probcons_codons_autop_version = "4.0.0"
probcons_codons_docker_version = "1.12"
probcons_codons_program_version = "1.12"
probcons_codons_emboss_docker_version = "6.6.0"
probcons_codons_emboss_program_version = "6.6.0"
probcons_codons_translatorx_docker_version = "01.09.2022"
probcons_codons_translatorx_program_version = "https://translatorx.org"
probcons_codons_seda_docker_version = "1.7.5-docker29.0.1"
probcons_codons_seda_program_version = "1.7.5"
probcons_ref = "Do CB, Mahabhashyam MS, Brudno M, Batzoglou S. (2005)"
probcons_doi = "10.1101/gr.2821705"
emboss_ref = "Rice, P., Longden, I., & Bleasby, A. (2000)"
emboss_doi = "10.1016/s0168-9525(00)02024-2"
translatorx_ref = "Abascal, F., Zardoya, R., & Telford, M. J. (2010)"
translatorx_doi = "10.1093/nar/gkq291"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global probcons_codons_autop_version, probcons_codons_docker_version, probcons_codons_program_version
    global probcons_codons_emboss_docker_version, probcons_codons_emboss_program_version
    global probcons_codons_translatorx_docker_version, probcons_codons_translatorx_program_version
    global probcons_codons_seda_docker_version, probcons_codons_seda_program_version
    global probcons_ref, probcons_doi, emboss_ref, emboss_doi, translatorx_ref, translatorx_doi, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "probcons_codons_docker_c_version",
                          "probcons_codons_emboss_docker_c_version",
                          "probcons_codons_translatorx_docker_c_version",
                          "probcons_codons_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["probcons_codons_docker_c_version"]:
        probcons_codons_autop_version = "?"
        probcons_codons_docker_version = config["probcons_codons_docker_c_version"]
        probcons_codons_program_version = "?"
        probcons_ref = "?"
        probcons_doi = "?"

    if config["probcons_codons_emboss_docker_c_version"]:
        probcons_codons_autop_version = "?"
        probcons_codons_emboss_docker_version = config["probcons_codons_emboss_docker_c_version"]
        probcons_codons_emboss_program_version = "?"
        emboss_ref = "?"
        emboss_doi = "?"

    if config["probcons_codons_translatorx_docker_c_version"]:
        probcons_codons_autop_version = "?"
        probcons_codons_translatorx_docker_version = config["probcons_codons_translatorx_docker_c_version"]
        probcons_codons_translatorx_program_version = "?"
        translatorx_ref = "?"
        translatorx_doi = "?"

    if config["probcons_codons_seda_docker_c_version"]:
        probcons_codons_autop_version = "?"
        probcons_codons_seda_docker_version = config["probcons_codons_seda_docker_c_version"]
        probcons_codons_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{probcons_codons_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    file_name = os.listdir(f"/data/{input_dir}")[0]

    step1_dir = f"/data/{prefix}1-PC_Translated_sequences"
    os.makedirs(step1_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/emboss:{probcons_codons_emboss_docker_version}", "transeq",
                    "-sequence", f"/data/{input_dir}/{file_name}", "-outseq", f"{step1_dir}/{file_name}.pep"])
    subprocess.run(start + ["reformat", "-id", step1_dir, "-od", step1_dir, "-rlb"])
    pep_path = f"{step1_dir}/{file_name}.pep"
    with open(pep_path) as f:
        content = f.read()
    with open(pep_path, "w") as f:
        f.write(re.sub(r"_1$", "", content, flags=re.MULTILINE))

    print("Aligning amino acid sequences with Probcons")
    step2_dir = f"/data/{prefix}2-PC_AA_sequence_alignment"
    os.makedirs(step2_dir, exist_ok=True)
    shell_cmd = f"probcons {pep_path} > {step2_dir}/{file_name}.pep_aligned"
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/probcons:{probcons_codons_docker_version}", "bash", "-c", shell_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(start + ["reformat", "-id", step2_dir, "-od", step2_dir, "-rlb"])

    print("Creating a nucleotide alignment using the amino acid alignment as a guide")
    step3_dir = f"/data/{prefix}3-PC_Nuc_sequence_alignment"
    os.makedirs(step3_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/translatorx:{probcons_codons_translatorx_docker_version}",
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
    if not re.search(r"^\s*Probcons_codons", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Probcons_codons {probcons_codons_autop_version},pegi3s/probcons:{probcons_codons_docker_version},'
                     f'Probcons {probcons_codons_program_version},"{probcons_ref}","{probcons_doi}"\n')
            f.write(f',pegi3s/emboss:{probcons_codons_emboss_docker_version},'
                    f'EMBOSS {probcons_codons_emboss_program_version},"{emboss_ref}","{emboss_doi}"\n')
            f.write(f',pegi3s/translatorx ({probcons_codons_translatorx_docker_version}),'
                    f'Translator X ({probcons_codons_translatorx_program_version}),'
                    f'"{translatorx_ref}","{translatorx_doi}"\n')
            f.write(f',pegi3s/seda:{probcons_codons_seda_docker_version},SEDA {probcons_codons_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'probcons_ref="{probcons_ref}"\nprobcons_doi="{probcons_doi}"\n')
        f.write(f'emboss_ref="{emboss_ref}"\nemboss_doi="{emboss_doi}"\n')
        # NOTE: mirrors a pre-existing bug in the original script (writes translatorx_ref twice instead of the doi)
        f.write(f'translatorx_ref="{translatorx_ref}"\ntranslatorx_ref="{translatorx_ref}"\n')
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    main()
