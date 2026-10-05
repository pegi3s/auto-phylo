#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys

ipssa_autop_version = "4.0.0"
ipssa_docker_version = "1.2.6"
ipssa_program_version = "1.2.6"
ipssa_ref = "López-Fernández, H., Vieira, C.P., Ferreira, P. et al. (2021)"
ipssa_doi = "10.1007/s12539-021-00439-2"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    global ipssa_autop_version, ipssa_docker_version, ipssa_program_version, ipssa_ref, ipssa_doi

    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("dir", "project", "ipssa_docker_c_version", "ipssa_sequence_limit", "ipssa_random_seed",
                          "ipssa_align_method", "ipssa_tcoffee_min_score", "ipssa_mrbayes_generations",
                          "ipssa_mrbayes_burnin", "ipssa_fubar_sequence_limit", "ipssa_fubar_runs",
                          "ipssa_codeml_sequence_limit", "ipssa_codeml_runs", "ipssa_codeml_models",
                          "ipssa_omegamap_sequence_limit", "ipssa_omegamap_runs", "ipssa_omegamap_iterations")
    data_dir = config["dir"]
    project = config["project"]

    if config["ipssa_docker_c_version"]:
        ipssa_autop_version = "?"
        ipssa_docker_version = config["ipssa_docker_c_version"]
        ipssa_program_version = "?"
        ipssa_ref = "?"
        ipssa_doi = "?"

    step1_dir = f"/data/{prefix}1-ipssa"
    project_dir = f"{step1_dir}/ipssa_project"
    input_subdir = f"{project_dir}/input"
    os.makedirs(input_subdir, exist_ok=True)
    os.makedirs(f"/data/{out_dir}", exist_ok=True)

    # docker-in-docker bind mounts need real host paths, not this container's /data view
    host_project_dir = f"{data_dir}/{prefix}1-ipssa/ipssa_project"
    host_input_dir = f"{host_project_dir}/input"
    host_pipeline_working_dir = f"{host_project_dir}/pipeline_working_dir"

    for f in glob.glob(f"/data/{input_dir}/*"):
        shutil.copy(f, input_subdir)

    params_lines = [
        "#", "### General parameters ###", "#", "",
        "# The maximum number of sequences to use for the master file",
        f"sequence_limit={config['ipssa_sequence_limit']}", "",
        "# The random seed",
        f"random_seed={config['ipssa_random_seed']}", "",
        "#", "### Alignment ###", "#", "",
        "# The alignment method: clustalw, muscle, kalign, t_coffee, or amap",
        f"align_method={config['ipssa_align_method']}", "",
        "# Minimum support value for amino acid positions in the alignment",
        f"tcoffee_min_score={config['ipssa_tcoffee_min_score']}", "",
        "#", "### MrBayes ###", "#", "",
        "# Number of iterations in MrBayes",
        f"mrbayes_generations={config['ipssa_mrbayes_generations']}", "",
        "# MrBayes burnin",
        f"mrbayes_burnin={config['ipssa_mrbayes_burnin']}", "",
        "#", "### FUBAR ###", "#", "",
        "# The maximum number of sequences to be used by FUBAR.",
        f"fubar_sequence_limit={config['ipssa_fubar_sequence_limit']}", "",
        "# The number of FUBAR runs",
        f"fubar_runs={config['ipssa_fubar_runs']}", "",
        "#", "### codeML ###", "#", "",
        "# The maximum number of sequences to be used by CodeML",
        f"codeml_sequence_limit={config['ipssa_codeml_sequence_limit']}", "",
        "# The number of CodeML runs",
        f"codeml_runs={config['ipssa_codeml_runs']}", "",
        "# The CodeML models to be run, one or more of: 1, 2, 7, and/or 8.",
        f"codeml_models={config['ipssa_codeml_models']}", "",
        "#", "### OmegaMap ###", "#", "",
        "# The maximum number of sequences to use in OmegaMap",
        f"omegamap_sequence_limit={config['ipssa_omegamap_sequence_limit']}", "",
        "# The number of OmegaMap runs",
        f"omegamap_runs={config['ipssa_omegamap_runs']}", "",
        "# The number of OmegaMap iterations",
        f"omegamap_iterations={config['ipssa_omegamap_iterations']}",
    ]
    with open(f"{project_dir}/ipssa-project.params", "w") as f:
        f.write("\n".join(params_lines) + "\n")

    pipeline_working_dir = f"{project_dir}/pipeline_working_dir"
    num_tasks = "6"
    subprocess.run(["docker", "run", "-v", "/tmp:/tmp", "-v", "/var/run/docker.sock:/var/run/docker.sock",
                    "-v", f"{host_pipeline_working_dir}:/working_dir", "-v", f"{host_input_dir}:/input",
                    "-v", f"{host_project_dir}:/params", "--rm", f"pegi3s/ipssa:{ipssa_docker_version}",
                    "-o", "--logs", "/working_dir/logs", "--num-tasks", num_tasks,
                    "-pa", "/params/ipssa-project.params", "--", "--host_working_dir", host_pipeline_working_dir],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f in glob.glob(f"{pipeline_working_dir}/results/tabulated/*"):
        shutil.copy(f, f"/data/{out_dir}")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*ipssa", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f'ipssa {ipssa_autop_version},pegi3s/ipssa:{ipssa_docker_version},'
                     f'ipssa {ipssa_program_version},"{ipssa_ref}","{ipssa_doi}"\n')

    refs_file = f"/data/{project}/intermediate_files/refs/tmp_references"
    with open(refs_file, "a") as f:
        f.write(f'ipssa_ref="{ipssa_ref}"\nipssa_doi="{ipssa_doi}"\n')


if __name__ == "__main__":
    print("Running IPSSA", flush=True)
    main()
