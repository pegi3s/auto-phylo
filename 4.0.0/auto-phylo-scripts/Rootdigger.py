#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

Rootdigger_autop_version = "4.0.0"
Rootdigger_docker_version = "2026.09.11"
Rootdigger_program_version = "2026.09.11"
rootdigger_ref = "Bettisworth, B., & Stamatakis, A. (2021)"
rootdigger_doi = "10.1186/s12859-021-03956-5"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global Rootdigger_autop_version, Rootdigger_docker_version, Rootdigger_program_version
    global rootdigger_ref, rootdigger_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "rootdigger_mode", "Rootdigger_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    mode = config["rootdigger_mode"]

    if config["Rootdigger_docker_c_version"]:
        Rootdigger_autop_version = "?"
        Rootdigger_docker_version = config["Rootdigger_docker_c_version"]
        Rootdigger_program_version = "?"
        rootdigger_ref = "?"
        rootdigger_doi = "?"

    input_path = f"/data/{input_dir}"
    os.makedirs(f"/data/{out_dir}")

    # NOTE: mirrors a pre-existing bug in the original script: due to how the outer quoting works,
    # "--{mode}" ends up as bash -c's unused $0 instead of being passed to ./rd
    shell_cmd = (f"cd /usr/local/bin && ./rd --msa {input_path}/*.nuc_aligned --tree {input_path}/*.nwk")
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/rootdigger:{Rootdigger_docker_version}", "bash", "-c", shell_cmd, f"--{mode}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in glob.glob(f"{input_path}/*.ckp"):
        os.remove(f)

    rooted_files = sorted(glob.glob(f"{input_path}/*.nwk.rooted.tree"))
    name = os.path.basename(rooted_files[0]).replace("nuc_aligned.nwk.", "")
    for f in rooted_files:
        shutil.move(f, f"/data/{out_dir}/{name}.nwk")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*Rootdigger", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'Rootdigger {Rootdigger_autop_version},pegi3s/rootdigger:{Rootdigger_docker_version},'
                     f'Rootdigger {Rootdigger_program_version},"{rootdigger_ref}","{rootdigger_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'rootdigger_ref="{rootdigger_ref}"\nrootdigger_doi="{rootdigger_doi}"\n')


if __name__ == "__main__":
    print("Rooting tree", flush=True)
    main()
