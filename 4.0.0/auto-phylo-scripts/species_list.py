#!/usr/bin/env python3
import glob
import os
import re
import shutil
import sys

species_list_autop_version = "4.0.0"


def main():
    input_dir, out_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

    out_path = f"/data/{out_dir}"
    step1_dir = f"/data/{prefix}1-Species_list"
    os.makedirs(out_path, exist_ok=True)
    os.makedirs(step1_dir, exist_ok=True)

    organisms = []
    for path in glob.glob(f"/data/{input_dir}/*"):
        with open(path) as f:
            for line in f:
                line = line.rstrip("\n")
                if line.startswith(">"):
                    line = line.replace(" ", "_")
                    organism = "_".join(line.split(">", 1)[1].split("_")[:2])
                    organisms.append(organism)

    # sort | uniq -c | sort -k2 : count occurrences of each species, sorted by species name
    counts = {}
    for species in sorted(organisms):
        counts[species] = counts.get(species, 0) + 1

    species_count_file = f"{out_path}/species_count"
    if os.path.exists(species_count_file):
        species_count_file = f"{out_path}/species_count_1"

    with open(species_count_file, "w") as f:
        for species in sorted(counts):
            f.write(f"{species} x{counts[species]}\n")

    shutil.copy(f"{out_path}/species_count", step1_dir)

    versions_file = "/data/files_to_keep/versions.csv"
    with open(versions_file) as f:
        versions_content = f.read()
    if not re.search(r"^\s*species_list", versions_content, re.MULTILINE):
        with open(versions_file, "a") as f:
            f.write(f"species_list {species_list_autop_version},,,\n")


if __name__ == "__main__":
    print("Creating a list with the species names", flush=True)
    main()
