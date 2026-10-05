#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

mrbayes_autop_version = "4.0.0"
mrbayes_docker_version = "3.2.7"
mrbayes_program_version = "3.2.7"
mrbayes_alter_docker_version = "1.3.4"
mrbayes_alter_program_version = "1.3.4"
mrbayes_bioconvert_docker_version = "1.2.0"
mrbayes_bioconvert_program_version = "1.2.0"
mrbayes_ref = "Huelsenbeck, J. P., & Ronquist, F. (2001)"
mrbayes_doi = "10.1093/bioinformatics/17.8.754"
alter_ref = "Glez-Peña D, Gómez-Blanco D, Reboiro-Jato M, Fdez-Riverola F, Posada D. (2010)"
alter_doi = "10.1093/nar/gkq321"
bioconvert_ref = "Caro H, Dollin S, Biton A, Brancotte B, Desvillechabrol D, Dufresne Y, Li B, Kornobis E, Lemoine F, Maillet N, Perrin A, Traut N, Néron B, Cokelaer T. (2023)"
bioconvert_doi = "10.1093/nargab/lqad074"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global mrbayes_autop_version, mrbayes_docker_version, mrbayes_program_version
    global mrbayes_alter_docker_version, mrbayes_alter_program_version
    global mrbayes_bioconvert_docker_version, mrbayes_bioconvert_program_version
    global mrbayes_ref, mrbayes_doi, alter_ref, alter_doi, bioconvert_ref, bioconvert_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "mb_ngen", "mb_burnin", "mrbayes_docker_c_version",
                          "mrbayes_alter_docker_c_version", "mrbayes_bioconvert_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    mb_ngen = config["mb_ngen"]
    mb_burnin = config["mb_burnin"]

    if config["mrbayes_docker_c_version"]:
        mrbayes_autop_version = "?"
        mrbayes_docker_version = config["mrbayes_docker_c_version"]
        mrbayes_program_version = "?"
        mrbayes_ref = "?"
        mrbayes_doi = "?"

    if config["mrbayes_alter_docker_c_version"]:
        mrbayes_autop_version = "?"
        mrbayes_alter_docker_version = config["mrbayes_alter_docker_c_version"]
        mrbayes_alter_program_version = "?"
        alter_ref = "?"
        alter_doi = "?"

    if config["mrbayes_bioconvert_docker_c_version"]:
        mrbayes_autop_version = "?"
        mrbayes_bioconvert_docker_version = config["mrbayes_bioconvert_docker_c_version"]
        mrbayes_bioconvert_program_version = "?"
        bioconvert_ref = "?"
        bioconvert_doi = "?"

    input_path = f"/data/{input_dir}"
    file_name = os.listdir(input_path)[0]

    print("Running MrBayes")
    with open(f"{input_path}/{file_name}") as f:
        lines = f.read().splitlines()
    truncated_path = f"{input_path}/{file_name}.truncated"
    with open(truncated_path, "w") as f:
        for header, sequence in zip(lines[0::2], lines[1::2]):
            f.write(header[:98] + "\n")
            f.write(sequence + "\n")

    step1_dir = f"/data/{prefix}1-ALTER_conversion"
    os.makedirs(step1_dir, exist_ok=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/alter:{mrbayes_alter_docker_version}", "-i", truncated_path,
                    "-o", f"{step1_dir}/alter_output.nex", "-ia", "-of", "NEXUS", "-oo", "Linux", "-op", "GENERAL"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    step2_dir = f"/data/{prefix}2-MrBayes"
    os.makedirs(step2_dir, exist_ok=True)
    nex_path = f"{step2_dir}/alter_output.nex"
    with open(f"{step1_dir}/alter_output.nex") as f:
        nex_lines = [l for l in f.read().splitlines() if "ABCDEFGHIKLMNOPQRSTUVWXYZ" not in l]
    nex_content = "\n".join(nex_lines) + "\n"
    nex_content = nex_content.replace("datatype=NUCLEOTIDE", "datatype=DNA")

    number = None
    for line in nex_lines:
        if "nchar=" in line:
            number = line.split("=")[2].rstrip(";")
            break

    mrbayes_block = [
        "begin mrbayes;",
        "set autoclose=yes nowarn=yes;",
        f"charset first_pos = 1-{number}\\3;",
        f"charset second_pos = 2-{number}\\3;",
        f"charset third_pos = 3-{number}\\3;",
        "partition by_codon = 3: first_pos,second_pos,third_pos;",
        "set partition = by_codon;",
        "lset nst=6 rates=invgamma;",
        "unlink shape=(3);",
        f"mcmc ngen={mb_ngen};",
        f"sump burnin={mb_burnin};",
        f"sumt conformat=simple burnin={mb_burnin};",
        "end;",
    ]
    nex_content += "\n".join(mrbayes_block) + "\n"
    with open(nex_path, "w") as f:
        f.write(nex_content)

    with open(f"{step2_dir}/log", "w") as log_file:
        subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}/{prefix}2-MrBayes:/data",
                        f"pegi3s/mrbayes:{mrbayes_docker_version}", "mb", "/data/alter_output.nex"],
                       stdout=log_file)

    step3_dir = f"/data/{prefix}3-MrBayes_tree"
    os.makedirs(step3_dir, exist_ok=True)
    con_tre_files = glob.glob(f"{step2_dir}/*.con.tre")
    with open(con_tre_files[0]) as f:
        con_tre_lines = f.read().splitlines()
    # replace the note-comment block (up to the next "end" line) with a plain "end;" line
    start_idx = next((i for i, l in enumerate(con_tre_lines)
                       if "[Note: This tree contains information only on the topology" in l), None)
    if start_idx is not None:
        end_idx = next(i for i in range(start_idx, len(con_tre_lines)) if "end" in con_tre_lines[i])
        con_tre_lines[start_idx:end_idx + 1] = ["end;"]
    with open(f"{step3_dir}/MrBayes.con.tre", "w") as f:
        f.write("\n".join(con_tre_lines) + "\n")

    print("Converting nexus to newick")
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/bioconvert:{mrbayes_bioconvert_docker_version}", "nexus2newick",
                    f"{step3_dir}/MrBayes.con.tre", f"{step3_dir}/MrBayes.con.tre.nwk"])

    os.makedirs(f"/data/{out_dir}", exist_ok=True)
    shutil.copy(f"{step3_dir}/MrBayes.con.tre.nwk", f"/data/{out_dir}/{file_name}.con.tre.nwk")
    os.remove(truncated_path)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*MrBayes", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'MrBayes {mrbayes_autop_version},pegi3s/mrbayes:{mrbayes_docker_version},'
                     f'MrBayes {mrbayes_program_version},"{mrbayes_ref}","{mrbayes_doi}"\n')
            f.write(f',pegi3s/alter:{mrbayes_alter_docker_version},'
                    f'Alter {mrbayes_alter_program_version},"{alter_ref}","{alter_doi}"\n')
            f.write(f',pegi3s/bioconvert:{mrbayes_bioconvert_docker_version},'
                    f'Bioconvert {mrbayes_bioconvert_program_version},"{bioconvert_ref}","{bioconvert_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'mrbayes_ref="{mrbayes_ref}"\nmrbayes_doi="{mrbayes_doi}"\n')
        f.write(f'alter_ref="{alter_ref}"\nalter_doi="{alter_doi}"\n')
        f.write(f'bioconvert_ref="{bioconvert_ref}"\nbioconvert_doi="{bioconvert_doi}"\n')


if __name__ == "__main__":
    main()
