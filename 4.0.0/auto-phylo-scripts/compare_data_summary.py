#!/usr/bin/env python3
import os
import re
import shutil
import sys

compare_data_summary_version = "4.0.0"


def main():
    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    out_path = f"/data/{out_dir}"
    step1_dir = f"/data/{prefix}1-Comparing_lists"
    os.makedirs(out_path, exist_ok=True)
    os.makedirs(step1_dir, exist_ok=True)

    list1, list2 = sorted(os.listdir(f"/data/{input_dir}"))[:2]

    with open(f"/data/{input_dir}/{list1}") as f:
        lines1 = f.read().splitlines()
    with open(f"/data/{input_dir}/{list2}") as f:
        lines2 = f.read().splitlines()

    combined = sorted(lines1 + lines2)
    counts = {}
    for line in combined:
        counts[line] = counts.get(line, 0) + 1
    different_species = [line for line in combined if counts[line] == 1]
    # uniq -d keeps only the first occurrence of each duplicated line
    common_species, seen = [], set()
    for line in combined:
        if counts[line] > 1 and line not in seen:
            common_species.append(line)
            seen.add(line)

    with open(f"{out_path}/different_species", "w") as f:
        f.write("\n".join(different_species) + ("\n" if different_species else ""))
    with open(f"{out_path}/common_species", "w") as f:
        f.write("\n".join(common_species) + ("\n" if common_species else ""))

    report = "\n".join([
        f"These are the common species between {list1} and {list2}:",
        *common_species,
        "",
        f"These are the different species between {list1} and {list2}:",
        *different_species,
    ]) + "\n"
    with open(f"{out_path}/species_comparison", "w") as f:
        f.write(report)

    for name in os.listdir(out_path):
        shutil.copy(f"{out_path}/{name}", step1_dir)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*compare_data_summary", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f"compare_data_summary {compare_data_summary_version},,,\n")


if __name__ == "__main__":
    print("Comparing lists", flush=True)
    main()
