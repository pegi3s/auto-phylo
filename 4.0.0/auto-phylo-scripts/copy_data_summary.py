#!/usr/bin/env python3
import os
import re
import shutil
import sys

copy_data_summary_version = "4.0.0"


def main():
    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    out_path = f"/data/{out_dir}"
    step1_dir = f"/data/{prefix}1-Copying_species_list"
    os.makedirs(out_path, exist_ok=True)
    os.makedirs(step1_dir, exist_ok=True)

    input_dir_name = os.path.basename(input_dir)
    src = f"/data/{input_dir}/species_list"
    shutil.copy(src, f"{out_path}/{input_dir_name}.species_list")
    shutil.copy(src, f"{step1_dir}/{input_dir_name}.species_list")

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*copy_data_summary", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f"copy_data_summary {copy_data_summary_version},,,\n")


if __name__ == "__main__":
    print("Copying species list files", flush=True)
    main()
