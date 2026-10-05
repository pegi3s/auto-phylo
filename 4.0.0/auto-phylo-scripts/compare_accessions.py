#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys

compare_accessions_autop_version = "4.0.0"


def read_config(*names):
    """Source /data/config with bash and return the requested variables."""
    script = "set -e\n. /data/config\n" + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names)
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def main():
    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    config = read_config("comp_acc_previous_list")
    list1 = config["comp_acc_previous_list"]
    list2 = sorted(os.listdir(f"/data/{input_dir}"))[0]

    out_path = f"/data/{out_dir}"
    step1_dir = f"/data/{prefix}1-Comparing_acc_lists"
    os.makedirs(out_path, exist_ok=True)
    os.makedirs(step1_dir, exist_ok=True)

    with open(f"/data/{list1}") as f:
        lines1 = f.read().splitlines()
    with open(f"/data/{input_dir}/{list2}") as f:
        lines2 = f.read().splitlines()

    combined = sorted(lines1 + lines2)
    counts = {}
    for line in combined:
        counts[line] = counts.get(line, 0) + 1
    # accession numbers present in only one of the two lists
    different_accessions = [line for line in combined if counts[line] == 1]

    base_counts = {}
    for line in different_accessions:
        base = line.split(".", 1)[0]
        base_counts[base] = base_counts.get(base, 0) + 1
    # base accessions appearing on both sides but with a different version suffix
    different_versions = sorted(base for base, count in base_counts.items() if count > 1)

    remaining = list(different_accessions)
    versions_1_parts = []
    for base in different_versions:
        matched = [line for line in remaining if base in line]
        versions_1_parts.append(" ".join(matched) + (" " if matched else ""))
        remaining = [line for line in remaining if not line.startswith(base + ".")]

    report = "\n".join([
        f"These accession numbers are different between {list1} and {list2}:",
        *remaining,
        "",
        f"There are different accession number versions when comparing {list2} and {list1} for:",
        "".join(versions_1_parts),
    ]) + "\n"
    with open(f"{out_path}/acc_numbers_comparison", "w") as f:
        f.write(report)

    for name in os.listdir(out_path):
        src = f"{out_path}/{name}"
        if os.path.isfile(src):
            shutil.copy(src, step1_dir)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*compare_accessions", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f"compare_accessions {compare_accessions_autop_version},,,\n")


if __name__ == "__main__":
    print("Comparing accession lists", flush=True)
    main()
