#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys

getlist_autop_version = "4.0.0"
getlist_entrezd_docker_version = "10.0.20180927"
getlist_entrezd_program_version = "10.0.20180927"
getlist_seda_docker_version = "1.7.5-docker29.0.1"
getlist_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"
entrez_direct_ref = "Kans J. (2013)"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def run_bash(data_dir, image, bash_cmd):
    return subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data", image, "bash", "-c", bash_cmd],
                          capture_output=True, text=True).stdout


def main():
    global getlist_autop_version, getlist_entrezd_docker_version, getlist_entrezd_program_version
    global getlist_seda_docker_version, getlist_seda_program_version, seda_ref, seda_doi, entrez_direct_ref

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "getlist_db",
                          "getlist_entrezd_docker_c_version", "getlist_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    getlist_db = config["getlist_db"]

    if config["getlist_entrezd_docker_c_version"]:
        getlist_autop_version = "?"
        getlist_entrezd_docker_version = config["getlist_entrezd_docker_c_version"]
        getlist_entrezd_program_version = "?"
        entrez_direct_ref = "?"

    if config["getlist_seda_docker_c_version"]:
        getlist_autop_version = "?"
        getlist_seda_docker_version = config["getlist_seda_docker_c_version"]
        getlist_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    step1_dir = f"/data/{prefix}1-getlist"
    out_path = f"/data/{out_dir}"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(out_path, exist_ok=True)

    input_file = None
    for root, _dirs, files in os.walk(f"/data/{input_dir}"):
        if files:
            input_file = os.path.join(root, sorted(files)[0])
            break

    with open(input_file) as f:
        queries = f.read().splitlines()

    entrez_image = f"pegi3s/entrez-direct:{getlist_entrezd_docker_version}"

    for query in queries:
        query_name = re.sub(r"[^A-Za-z0-9_]", "", query.replace(" ", "_"))
        output_file = f"{out_path}/{query_name}_acc_numbers"

        rep_cmd = (f"esearch -db assembly -query '{query}[orgn] AND "
                   f'"representative genome"[RefSeq Category]\' | efetch -format docsum | '
                   f"xtract -pattern DocumentSummary -element AssemblyAccession")
        ref_cmd = (f"esearch -db assembly -query '{query}[orgn] AND "
                   f'"reference genome"[RefSeq Category]\' | efetch -format docsum | '
                   f"xtract -pattern DocumentSummary -element AssemblyAccession")

        with open(output_file, "w") as f:
            f.write(run_bash(data_dir, entrez_image, rep_cmd))
            f.write(run_bash(data_dir, entrez_image, ref_cmd))

        with open(output_file) as f:
            acc_numbers = f.read().splitlines()

        temp_lines = []
        for acc_number in acc_numbers:
            if getlist_db == "genbank" and acc_number.startswith("GCF"):
                lookup_cmd = (f'esearch -db assembly -query "{acc_number}" | efetch -format docsum | '
                              f"xtract -pattern DocumentSummary -element Genbank")
                gca = run_bash(data_dir, entrez_image, lookup_cmd).strip()
                if gca:
                    temp_lines.append(gca)
            elif getlist_db == "refseq" and acc_number.startswith("GCA"):
                lookup_cmd = (f'esearch -db assembly -query "{acc_number}" | efetch -format docsum | '
                              f"xtract -pattern DocumentSummary -element RefSeq")
                gcf = run_bash(data_dir, entrez_image, lookup_cmd).strip()
                if gcf:
                    temp_lines.append(gcf)
            else:
                temp_lines.append(acc_number)

        temp_file = f"{out_path}/{query_name}_temp_file"
        with open(temp_file, "w") as f:
            f.write("\n".join(temp_lines) + ("\n" if temp_lines else ""))

        shutil.move(output_file, step1_dir)
        if getlist_db not in ("genbank", "refseq"):
            getlist_db = "genbank_refseq"
        shutil.move(temp_file, f"{out_path}/{query_name}_{getlist_db}_acc")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*getlist", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'getlist {getlist_autop_version},pegi3s/entrez-direct:{getlist_entrezd_docker_version},'
                     f'Entrez-Direct {getlist_entrezd_program_version},"{entrez_direct_ref}",\n')
            f.write(f',pegi3s/seda:{getlist_seda_docker_version},SEDA {getlist_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'entrez_direct_ref="{entrez_direct_ref}"\n')
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("Getting the NCBI accession numbers", flush=True)
    main()
