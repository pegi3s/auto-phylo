#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

tblastn_autop_version = "4.0.0"
tblastn_blast_docker_version = "2.17.0"
tblastn_blast_program_version = "2.17.0"
tblastn_seda_docker_version = "1.7.5-docker29.0.1"
tblastn_seda_program_version = "1.7.5"
tblastn_utilities_docker_version = "0.25.0"
tblastn_utilities_program_version = "0.25.0"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global tblastn_autop_version, tblastn_blast_docker_version, tblastn_blast_program_version
    global tblastn_seda_docker_version, tblastn_seda_program_version
    global tblastn_utilities_docker_version, tblastn_utilities_program_version, seda_ref, seda_doi

    tblastn_input_dir, tblastn_results_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "tblastn_query", "tblastn_expect",
                          "tblastn_blast_docker_c_version", "tblastn_seda_docker_c_version",
                          "tblastn_utilities_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    query = config["tblastn_query"]
    expect = config["tblastn_expect"]

    if config["tblastn_blast_docker_c_version"]:
        tblastn_autop_version = "?"
        tblastn_blast_docker_version = config["tblastn_blast_docker_c_version"]
        tblastn_blast_program_version = "?"

    if config["tblastn_seda_docker_c_version"]:
        tblastn_autop_version = "?"
        tblastn_seda_docker_version = config["tblastn_seda_docker_c_version"]
        tblastn_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    if config["tblastn_utilities_docker_c_version"]:
        tblastn_autop_version = "?"
        tblastn_utilities_docker_version = config["tblastn_utilities_docker_c_version"]
        tblastn_utilities_program_version = "?"

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{tblastn_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    os.makedirs("/data/tmp/reformat", exist_ok=True)
    os.makedirs(f"/data/{tblastn_results_dir}", exist_ok=True)
    os.makedirs(f"/data/{prefix}1-tblastn", exist_ok=True)

    names = sorted(n for n in os.listdir(f"/data/{tblastn_input_dir}") if n != "tmp:" and n.strip())

    for name in names:
        shutil.copy(f"/data/{tblastn_input_dir}/{name}", "/data/tmp/reformat/")
        subprocess.run(start + ["reformat", "-id", "/data/tmp/reformat", "-od", "/data/tmp/reformat", "-rlb"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.move(f"/data/tmp/reformat/{name}", "/data/tmp/input_original")

        with open("/data/tmp/input_original") as f:
            lines = f.read().splitlines()

        with open("/data/tmp/input", "w") as out:
            for header, sequence in zip(lines[0::2], lines[1::2]):
                out.write(header[:48].split(" ")[0] + "\n")
                out.write(sequence.split(" ")[0] + "\n")

        subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}/tmp:/data",
                        f"pegi3s/utilities:{tblastn_utilities_docker_version}",
                        "fasta_remove_line_breaks", "/data/input"])
        subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                        f"pegi3s/blast:{tblastn_blast_docker_version}", "makeblastdb", "-in", "/data/tmp/input",
                        "-out", f"/data/tmp/{name}", "-dbtype", "nucl", "-parse_seqids"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                        f"pegi3s/blast:{tblastn_blast_docker_version}", "tblastn", "-query", f"/data/{query}",
                        "-db", f"/data/tmp/{name}", "-evalue", expect, "-outfmt", "6",
                        "-out", f"/data/tmp/{name}.output"])

        for ext in ("ndb", "nhr", "nin", "njs", "nog", "nos", "not", "nsq", "ntf", "nto"):
            for db_file in glob.glob(f"/data/tmp/*.{ext}"):
                os.remove(db_file)

        with open(f"/data/tmp/{name}.output") as f:
            unique_ids = sorted({line.split("\t")[1] for line in f if line.strip()})

        result_path = f"/data/{tblastn_results_dir}/{name}"
        with open(result_path, "w") as out:
            for uid in unique_ids:
                for i, line in enumerate(lines):
                    if uid in line:
                        out.write(line + "\n")
                        if i + 1 < len(lines):
                            out.write(lines[i + 1] + "\n")

        if os.path.exists(result_path) and os.path.getsize(result_path) > 0:
            with open(result_path) as f:
                content = f.read()
            with open(result_path, "w") as f:
                f.write(content.replace("lcl|", ""))

        shutil.move(f"/data/tmp/{name}.output", f"/data/{prefix}1-tblastn/")

    shutil.rmtree("/data/tmp/reformat")
    for tmp_file in glob.glob("/data/tmp/*"):
        os.remove(tmp_file)
    os.rmdir("/data/tmp")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*tblastn", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f"tblastn {tblastn_autop_version},pegi3s/blast:{tblastn_blast_docker_version},"
                     f"BLAST {tblastn_blast_program_version},,\n")
            f.write(f",pegi3s/seda:{tblastn_seda_docker_version},SEDA {tblastn_seda_program_version},"
                    f'"{seda_ref}","{seda_doi}"\n')
            f.write(f",pegi3s/utilities:{tblastn_utilities_docker_version},"
                    f"utilities {tblastn_utilities_program_version},,\n")

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    print("tblastn", flush=True)
    main()
