#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

view_trees_autop_version = "4.0.0"
view_trees_newick_utils_docker_version = "1.6"
view_trees_newick_utils_program_version = "1.6"
newick_utils_ref = "Junier T, Zdobnov EM. (2010)"
newick_utils_doi = "10.1093/bioinformatics/btq243"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global view_trees_autop_version, view_trees_newick_utils_docker_version
    global view_trees_newick_utils_program_version, newick_utils_ref, newick_utils_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "vt_show_branch_length", "vt_support_cutoff", "vt_columns",
                          "view_trees_newick_utils_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]

    if config["view_trees_newick_utils_docker_c_version"]:
        view_trees_autop_version = "?"
        view_trees_newick_utils_docker_version = config["view_trees_newick_utils_docker_c_version"]
        view_trees_newick_utils_program_version = "?"
        newick_utils_ref = "?"
        newick_utils_doi = "?"

    a = "" if config["vt_show_branch_length"] == "y" else " -b 'visibility:hidden'"

    step1_dir = f"/data/{prefix}1-display_trees"
    out_path = f"/data/{out_dir}"
    os.makedirs(step1_dir, exist_ok=True)
    os.makedirs(out_path, exist_ok=True)
    input_file = os.path.basename(sorted(glob.glob(f"/data/{input_dir}/*.nwk"))[0])

    shell_cmd = (f"nw_ed /data/{input_dir}/{input_file} 'b < {config['vt_support_cutoff']}' o > tmp.svg && "
                 f"nw_display -w {config['vt_columns']} {a} -s tmp.svg > {out_path}/{input_file}.svg")
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/newick_utils:{view_trees_newick_utils_docker_version}", "bash", "-c", shell_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    svg_path = f"{out_path}/{input_file}.svg"
    with open(svg_path) as f:
        content = f.read()
    with open(svg_path, "w") as f:
        f.write(content.replace("<defs><style type",
                                 '\n<rect width="100%" height="100%" fill="white"/>\n<defs><style type'))
    shutil.copy(svg_path, step1_dir)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*view_trees", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'view_trees {view_trees_autop_version},'
                     f'pegi3s/newick_utils:{view_trees_newick_utils_docker_version},'
                     f'newick-utils {view_trees_newick_utils_program_version},'
                     f'"{newick_utils_ref}","{newick_utils_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'newick_utils_ref="{newick_utils_ref}"\nnewick_utils_doi="{newick_utils_doi}"\n')


if __name__ == "__main__":
    print("Displaying Newick trees", flush=True)
    main()
