#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

tree_collapse_autop_version = "4.0.0"
tree_collapse_docker_version = "1.3.0"
tree_collapse_program_version = "1.3.0"
tree_collapse_seda_docker_version = "1.7.5-docker29.0.1"
tree_collapse_seda_program_version = "1.7.5"
seda_ref = "Lopez-Fernandez, H., Duque, P., Vazquez, N., Fdez-Riverola, F., Reboiro-Jato, M., Vieira, C. P., & Vieira, J. (2022)"
seda_doi = "10.1109/TCBB.2020.3040383"

# grep -oE '[A-Za-z_]+_[A-Za-z_]+_[A-Za-z_]+_[0-9_]+_[A-Z]+_[0-9_]+|[A-Za-z_]+_[0-9_]+:[0-9.]+'
HEADER_PATTERN = re.compile(
    r"[A-Za-z_]+_[A-Za-z_]+_[A-Za-z_]+_[0-9_]+_[A-Z]+_[0-9_]+|[A-Za-z_]+_[0-9_]+:[0-9.]+"
)


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def grep_a1(lines, header):
    pattern = re.compile("^>" + re.escape(header))
    result = []
    for i, line in enumerate(lines):
        if pattern.search(line):
            result.append(line)
            if i + 1 < len(lines):
                result.append(lines[i + 1])
    return result


def main():
    global tree_collapse_autop_version, tree_collapse_docker_version, tree_collapse_program_version
    global tree_collapse_seda_docker_version, tree_collapse_seda_program_version, seda_ref, seda_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "tc_taxonomy", "tc_stsm", "tc_output", "interest_species",
                          "tree_collapse_docker_c_version", "tree_collapse_seda_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    tc_taxonomy = config["tc_taxonomy"]
    tc_stsm = config["tc_stsm"]
    tc_output = config["tc_output"]
    interest_species = config["interest_species"]

    if config["tree_collapse_docker_c_version"]:
        tree_collapse_autop_version = "?"
        tree_collapse_docker_version = config["tree_collapse_docker_c_version"]
        tree_collapse_program_version = "?"

    if config["tree_collapse_seda_docker_c_version"]:
        tree_collapse_autop_version = "?"
        tree_collapse_seda_docker_version = config["tree_collapse_seda_docker_c_version"]
        tree_collapse_seda_program_version = "?"
        seda_ref = "?"
        seda_doi = "?"

    print("Collapsing the tree...")
    step1_dir = f"/data/{prefix}1-Collapsed_tree"
    out_path = f"/data/{out_dir}"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(out_path, exist_ok=True)
    input_path = f"/data/{input_dir}"
    file_name = os.listdir(input_path)[0]

    start = ["docker", "run", "--rm", "-v", f"{data_dir}:/data",
             f"pegi3s/seda:{tree_collapse_seda_docker_version}", "/opt/SEDA/run-cli.sh"]

    # the *.nwk glob is expanded by the outer shell in the original script
    nwk_files = sorted(glob.glob(f"{input_path}/*.nwk")) or [f"{input_path}/*.nwk"]
    base_cmd = ["docker", "run", "--rm", "-v", "/var/run/docker.sock:/var/run/docker.sock",
                "-v", f"{data_dir}:/data", f"pegi3s/phylogenetic-tree-collapser:{tree_collapse_docker_version}",
                "collapse-tree.py", "--input"] + nwk_files + ["--input-format", "newick"]

    if not tc_taxonomy:
        subprocess.run(base_cmd + ["--output", f"{step1_dir}/{file_name}.tree_collapsed",
                                    "--output-type", "phylogram", "--output-collapsed-nodes",
                                    f"{step1_dir}/{file_name}.collapsed_nodes"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.move(f"{input_path}/{file_name}.sequence_to_species_mapping", step1_dir)
        shutil.move(f"{input_path}/{file_name}.taxonomy", step1_dir)
    else:
        subprocess.run(base_cmd + ["--taxonomy", f"/data/{tc_taxonomy}", "--sequence-mapping", f"/data/{tc_stsm}",
                                    "--output", f"{step1_dir}/{file_name}.tree_collapsed",
                                    "--output-type", "phylogram", "--output-collapsed-nodes",
                                    f"{step1_dir}/{file_name}.collapsed_nodes"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("estou aqui", out_dir)
    for f in glob.glob(f"{step1_dir}/*.tree_collapsed"):
        shutil.copy(f, out_path)
    for f in glob.glob(f"{step1_dir}/*.collapsed_nodes"):
        shutil.copy(f, out_path)
    for f in glob.glob(f"{input_path}/*.nwk"):
        shutil.copy(f, out_path)

    collapsed_headers = []
    for f in sorted(glob.glob(f"{out_path}/*.tree_collapsed")):
        with open(f) as fh:
            content = fh.read()
        collapsed_headers += [m.split(":")[0] for m in HEADER_PATTERN.findall(content)]
    with open(f"{out_path}/tc_collapsed_headers", "w") as f:
        f.write("\n".join(collapsed_headers) + ("\n" if collapsed_headers else ""))

    nuc_aligned_file = None
    for root, _dirs, files in sorted(os.walk("/data/")):
        for name in sorted(files):
            if name.endswith(".nuc_aligned"):
                nuc_aligned_file = os.path.join(root, name)
                break
        if nuc_aligned_file:
            break

    with open(nuc_aligned_file) as f:
        nuc_lines = f.read().splitlines()

    output_path = f"{out_path}/selected_sequences"
    output_lines = []

    if interest_species and os.path.exists(f"/data/{interest_species}") and os.path.getsize(f"/data/{interest_species}") > 0:
        with open(f"/data/{interest_species}") as f:
            species_of_interest = f.read().splitlines()
    else:
        species_of_interest = []

    collapsed_nodes_lines = []
    for f in sorted(glob.glob(f"{out_path}/*.collapsed_nodes")):
        with open(f) as fh:
            collapsed_nodes_lines += fh.read().splitlines()

    for header in collapsed_headers:
        direct_match = grep_a1(nuc_lines, header)
        if direct_match:
            output_lines += direct_match
            continue

        matched = [l for l in collapsed_nodes_lines if header in l]
        related_nodes = [l.split()[1] for l in matched]
        to_add = ["_" + l.split()[0] for l in matched]

        sequence_added = False
        for node in related_nodes:
            for species in species_of_interest:
                if species in node and grep_a1(nuc_lines, node):
                    output_lines += grep_a1(nuc_lines, node)
                    if to_add:
                        output_lines[-2] += to_add[0]
                    sequence_added = True

        if not species_of_interest or not sequence_added:
            first_node = related_nodes[0]
            output_lines += grep_a1(nuc_lines, first_node)
            if to_add:
                output_lines[-2] += to_add[0]

    with open(output_path, "w") as f:
        f.write("\n".join(output_lines) + ("\n" if output_lines else ""))

    if tc_output == "1":
        os.remove(f"{out_path}/tc_collapsed_headers")
        os.remove(output_path)
        for f in glob.glob(f"{out_path}/*.nwk"):
            os.remove(f)
    elif tc_output == "2":
        print("Getting selected sequences")
        shutil.move(f"{out_path}/tc_collapsed_headers", step1_dir)
        for f in glob.glob(f"{out_path}/*.tree_collapsed"):
            os.remove(f)
        for f in glob.glob(f"{out_path}/*.collapsed_nodes"):
            os.remove(f)
        for f in glob.glob(f"{out_path}/*.nwk"):
            os.remove(f)
        subprocess.run(start + ["undo-alignment", "-id", out_path, "-od", out_path, "-rlb"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*tree_collapse", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'tree_collapse {tree_collapse_autop_version},'
                     f'pegi3s/phylogenetic-tree-collapser:{tree_collapse_docker_version},'
                     f'Phylogenetic Tree Collapser {tree_collapse_program_version},,\n')
            f.write(f',pegi3s/seda:{tree_collapse_seda_docker_version},SEDA {tree_collapse_seda_program_version},'
                    f'"{seda_ref}","{seda_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'seda_ref="{seda_ref}"\nseda_doi="{seda_doi}"\n')


if __name__ == "__main__":
    main()

