#!/usr/bin/env python3
import os
import re
import shutil
import sys

split_autop_version = "4.0.0"


def main():
    input_dir, dir_number = sys.argv[1], int(sys.argv[2])

    i = 0
    for name in sorted(os.listdir(f"/data/{input_dir}")):
        i += 1
        if i > dir_number:
            i = 1
        target_dir = f"/data/{input_dir}.{i}"
        os.makedirs(target_dir, exist_ok=True)
        shutil.copy(f"/data/{input_dir}/{name}", target_dir)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*split", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f"split {split_autop_version},,,\n")


if __name__ == "__main__":
    main()
