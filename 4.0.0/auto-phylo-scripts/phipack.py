#!/usr/bin/env python3
import glob
import os
import re
import subprocess
import sys

phipack_autop_version = "4.0.0"
phipack_docker_version = "1.0.0"
phipack_program_version = "1.0.0"
phipack_ref = "Bruen, T. C., Philippe, H., & Bryant, D. (2006)"
phipack_doi = "10.1534/genetics.105.048975"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global phipack_autop_version, phipack_docker_version, phipack_program_version, phipack_ref, phipack_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "phipack_permutations", "phipack_docker_c_version")
    data_dir = config["dir"]
    project = config["project"]
    permutations = config["phipack_permutations"]

    if config["phipack_docker_c_version"]:
        phipack_autop_version = "?"
        phipack_docker_version = config["phipack_docker_c_version"]
        phipack_program_version = "?"
        phipack_ref = "?"
        phipack_doi = "?"

    out_path = f"/data/{out_dir}"
    os.makedirs(out_path, exist_ok=True)

    # the glob is expanded by the outer shell in the original script, before being embedded in the inner bash -c string
    files = sorted(glob.glob(f"/data/{input_dir}/*")) or [f"/data/{input_dir}/*"]
    shell_cmd = f"Phi -f {' '.join(files)} -p {permutations} -o > {out_path}/phipack_output"
    subprocess.run(["docker", "run", "--rm", "-v", f"{data_dir}:/data",
                    f"pegi3s/phipack:{phipack_docker_version}", "bash", "-c", shell_cmd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*phipack", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'phipack {phipack_autop_version},pegi3s/phipack:{phipack_docker_version},'
                     f'PhiPack {phipack_program_version},"{phipack_ref}","{phipack_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'phipack_ref="{phipack_ref}"\nphipack_doi="{phipack_doi}"\n')


if __name__ == "__main__":
    print("Executing Phipack", flush=True)
    main()
