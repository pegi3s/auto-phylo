#!/usr/bin/env python3
import glob
import os
import subprocess
from datetime import date

pipeline_summary_autop_version = "4.0.0"

REF_TOOLS = ["autophylo", "alter", "bioconvert", "clustalomega", "emboss", "fastroot", "fasttree", "ipssa",
             "jmodeltest", "kaks", "mafft", "megaxcc", "mrbayes", "muscle", "phipack", "probcons", "raxml",
             "rootdigger", "seda", "tcoffee", "translatorx", "newick_utils"]

CONFIG_VARS = [
    "project", "getlist_db", "include", "database_type", "add_refs_reference", "add_tax_taxonomy_header",
    "cgf_cga_reformat_headers", "CDS_processing_max_size_difference", "CDS_processing_reference_file",
    "CDS_processing_pattern", "check_cont_taxonomy", "check_cont_category", "data_summary_taxonomy",
    "get_phylo_taxa_name1", "blastn_query", "blastn_expect", "tblastn_query", "tblastn_expect",
    "tblastx_query", "tblastx_expect", "me_tree_bootstrap", "me_tree_treatment", "ml_tree_bootstrap",
    "ml_tree_treatment", "mp_tree_bootstrap", "mp_tree_treatment", "nj_tree_bootstrap", "nj_tree_treatment",
    "upgma_tree_bootstrap", "upgma_tree_treatment", "mb_ngen", "mb_burnin", "fastroot_rooting_method",
    "rootdigger_mode", "vt_show_branch_length", "vt_support_cutoff", "cga_selection_criterion",
    "cga_selection_correction", "cga_expect1", "cga_hit_region_window1", "cga_min_overlap", "cga_max_dist",
    "cga_intron_bp", "cga_min_full_nucleotide_size", "ipssa_random_seed", "ipssa_omegamap_runs",
    "phipack_permutations", "kaks_model", "probcons_refin_iterations",
]

REF_DOI_VARS = [f"{name}_{suffix}" for name in REF_TOOLS for suffix in ("ref", "doi")]


def read_vars():
    """Source /data/config and the accumulated tmp_references file with bash."""
    names = CONFIG_VARS + REF_DOI_VARS
    script = ("set -e\n"
              ". /data/config\n"
              'mkdir -p "/data/$project/intermediate_files/refs"\n'
              'touch "/data/$project/intermediate_files/refs/tmp_references"\n'
              '. "/data/$project/intermediate_files/refs/tmp_references"\n'
              + "\n".join(f'printf \'%s\\n\' "${name}"' for name in names))
    output = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout
    return dict(zip(names, output.split("\n")))


def count_files(path):
    return sum(len(files) for _root, _dirs, files in os.walk(path))


def count_headers(path):
    with open(path) as f:
        return sum(1 for line in f if line.startswith(">"))


def main():
    v = read_vars()
    v["autophylo_ref"] = "López-Fenández, H., Pinto, M., Vieira, C.P., Duque, P., Reboiro-Jato, M., Vieira, J. (2023)"
    v["autophylo_doi"] = "10.1007/978-3-031-38079-2_3"

    project = v["project"]
    refs_dir = f"/data/{project}/intermediate_files/refs"
    os.makedirs(refs_dir, exist_ok=True)
    pipsum_ref = f"{refs_dir}/pipsum_ref"
    pipsum_doi = f"{refs_dir}/pipsum_doi"

    pipeline_file = None
    for root, _dirs, files in sorted(os.walk("/data/")):
        if "pipeline" in files:
            pipeline_file = os.path.join(root, "pipeline")
            break

    with open(pipeline_file) as f:
        pipeline_lines_raw = [l for l in f.read().splitlines() if l.strip()]
    num_lines_pipeline = len(pipeline_lines_raw)

    with open(pipsum_ref, "a") as f:
        f.write(f'Auto-Phylo: "{v["autophylo_doi"]}", "{v["autophylo_ref"]}"\n')
    with open(pipsum_doi, "a") as f:
        f.write(f'Auto-Phylo: "{v["autophylo_ref"]}", "{v["autophylo_doi"]}"\n')

    def process_pipeline(suffix):
        def V(name):
            return v.get(f"{name}_{suffix}", "")

        summary_file = f"/data/files_to_keep/pipeline_summary_{suffix}"
        current_date = date.today().strftime("%d-%m-%Y")

        with open(summary_file, "a") as f:
            f.write("                                                          Auto-Phylo Pipeline Summary\n")
            f.write("\n")
            f.write("================================================================================\n")
            f.write("\n")
            f.write(f"This pipeline was run on the {current_date} using the auto-phylo software "
                    f"({V('autophylo')}) that is available as a Docker image at the pegi3s Bioinformatics "
                    f"Docker Images Project 'https://pegi3s.github.io/dockerfiles/'. During this run "
                    f"{num_lines_pipeline} modules were used. The pipeline summary is presented below. "
                    f"Detailed information on each module can be found at the auto-phylo website: "
                    f"'http://evolution6.i3s.up.pt/static/auto-phylo/v3/docs/index.html'.\n")

        nr_files_input_p = None
        nr_files_output_p = None

        for line in pipeline_lines_raw:
            parts = line.split()
            module, input_p, output_p = parts[0], parts[1], parts[2]
            split_used = parts[3] if len(parts) > 3 else ""
            nr_folders = parts[4] if len(parts) > 4 else ""

            input_dir_path = f"/data/{project}/{input_p}"
            output_dir_path = f"/data/{project}/{output_p}"

            if os.path.isdir(input_dir_path):
                nr_files_input_p = count_files(input_dir_path)
            if os.path.isdir(output_dir_path):
                nr_files_output_p = count_files(output_dir_path)

            split_text = ""
            if split_used == "split":
                split_text = (f" Along with this module, the split module was also used which divided the "
                              f"input directory files into {nr_folders} equally sized subfolders and each "
                              f"was processed individually to avoid computer overload.")

            with open(summary_file, "a") as f:
                # DATA ACQUISITION

                if module == "ncbi_retrieve":
                    input_files = sorted(glob.glob(f"{input_dir_path}/*")) if os.path.isdir(input_dir_path) else []
                    file_path = input_files[0] if input_files else None
                    if file_path and os.path.isfile(file_path):
                        with open(file_path) as ff:
                            lines_count = sum(1 for _ in ff)
                        include_text = {
                            "GENOME_FASTA": "genome FASTA", "GENOME_GFF": "genome GFF format",
                            "RNA_FASTA": "RNA FASTA", "CDS_FASTA": "CDS FASTA",
                            "PROT_FASTA": "protein FASTA", "SEQUENCE_REPORT": "a report of the",
                        }.get(v["include"])
                        if v["database_type"] == "assembly":
                            f.write(f"The {module} module accepted as input a file from the '{input_p}' "
                                    f"directory with {lines_count} NCBI accession numbers to be considered "
                                    f"but only {include_text} sequences were downloaded. The output files "
                                    f"({nr_files_output_p}) were generated in the '{output_p}' directory "
                                    f"along with a log file containing the sequences download information "
                                    f"for each accession number.\n")
                        elif v["database_type"] == "nucleotide":
                            f.write(f"The {module} module accepted as input a file from the '{input_p}' "
                                    f"directory with {lines_count} NCBI accession numbers to be considered. "
                                    f"The output files ({nr_files_output_p}) were generated in the "
                                    f"'{output_p}' directory along with a log file containing the sequences "
                                    f"download information for each accession number.\n")

                if module == "getlist":
                    input_files = sorted(glob.glob(f"{input_dir_path}/*")) if os.path.isdir(input_dir_path) else []
                    file_path = input_files[0] if input_files else None
                    if file_path and os.path.isfile(file_path):
                        with open(file_path, "rb") as ff:
                            raw = ff.read().decode()
                        query_lines = raw.splitlines()
                        line_count = len(query_lines)
                        if line_count == 1:
                            input_file_text = query_lines[0]
                            f.write(f"The {module} module accepted as input a single file from the "
                                    f"'{input_p}' directory containing the following query: "
                                    f"{input_file_text}. It then fetched the assembly data from the NCBI "
                                    f"{v['getlist_db']} database and returned as output a file containing "
                                    f"all the NCBI accession numbers available for that query in the "
                                    f"specified database. The output files were generated in the "
                                    f"'{output_p}' directory.\n")
                        else:
                            # tr '\n' ', ' only substitutes the first char of the target set (',') per source char
                            input_file_text = raw.replace("\n", ",")
                            f.write(f"The {module} module accepted as input a single file from the "
                                    f"'{input_p}' directory containing the following queries: "
                                    f"{input_file_text}. It then fetched the assembly data from the NCBI "
                                    f"{v['getlist_db']} database and returned as output a file for each "
                                    f"query containing all the NCBI accession numbers available in the "
                                    f"specified database. The output files were generated in the "
                                    f"'{output_p}' directory.\n")

                # BLAST Modules

                if module == "blastn":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and returned {nr_files_output_p} FASTA files containing "
                            f"all the sequences that showed a significant blastn hit. The query file used "
                            f"was '{v['blastn_query']}' and the BLAST was run with a {v['blastn_expect']} "
                            f"expect value.{split_text} The output files were generated in the "
                            f"'{output_p}' directory.\n")
                elif module == "tblastn":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and returned {nr_files_output_p} FASTA files containing "
                            f"all the sequences that showed a significant tblastn hit. The query file used "
                            f"was '{v['tblastn_query']}' and the BLAST was run with a {v['tblastn_expect']} "
                            f"expect value.{split_text} The output files were generated in the "
                            f"'{output_p}' directory.\n")
                elif module == "tblastx":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and returned {nr_files_output_p} FASTA files containing "
                            f"all the sequences that showed a significant tblastx hit. The query file used "
                            f"was '{v['tblastx_query']}' and the BLAST was run with a {v['tblastx_expect']} "
                            f"expect value.{split_text} The output files were generated in the "
                            f"'{output_p}' directory.\n")

                # FASTA FILE PROCESSING Modules

                if module == "add_refs":
                    path = f"/data/{v['add_refs_reference']}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted a single input FASTA file from the "
                                f"'{input_p}' directory containing {num_sequences} reference sequences to "
                                f"be added to the files located in the input directory.{split_text} The "
                                f"output files were generated in the '{output_p}' directory.\n")
                elif module == "add_taxonomy":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} files from the "
                            f"'{input_p}' directory and by quering the NCBI website with Entrez Direct "
                            f"(Kans J. (2013)), it added the respective {v['add_tax_taxonomy_header']} "
                            f"taxonomy to the headers of the FASTA files using SEDA-CLI ({V('seda')}) "
                            f"operations.{split_text} The output files ({nr_files_output_p}) were generated "
                            f"in the '{output_p}' directory.\n")
                    with open(pipsum_ref, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                    with open(pipsum_doi, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "CDS_processing":
                    if v["cgf_cga_reformat_headers"] == "y":
                        f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from "
                                f"the '{input_p}' directory and using SEDA-CLI ({V('seda')}) it implemented "
                                f"the following operations: 1) sequence headers were reformatted in order to "
                                f"keep only the scaffold and protein accession numbers, 2) sequences showing "
                                f"ambiguous nucleotides were removed; 3) only sequences showing a valid start "
                                f"codon, that do not have in frame stop codons, and that are multiple of "
                                f"three were kept, 4) stop codons were removed; 5) sequences showing a "
                                f"{v['CDS_processing_max_size_difference']}% size variation greater than the "
                                f"reference sequence ({v['CDS_processing_reference_file']}) were removed; "
                                f"6) only sequences showing the '{v['CDS_processing_pattern']}' pattern were "
                                f"kept and 7) isoforms were removed.{split_text} The output files "
                                f"({nr_files_output_p}) were generated in the '{output_p}' directory.\n")
                    else:
                        f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from "
                                f"the '{input_p}' directory and using SEDA-CLI ({V('seda')}) it implemented "
                                f"the following operations: 1) sequences showing ambiguous nucleotides were "
                                f"removed; 2) only sequences showing a valid start codon, that do not have "
                                f"in frame stop codons, and that are multiple of three were kept, 3) stop "
                                f"codons were removed; 4) sequences showing a "
                                f"{v['CDS_processing_max_size_difference']}% size variation greater than the "
                                f"reference sequence ({v['CDS_processing_reference_file']}) were removed; "
                                f"5) only sequences showing the '{v['CDS_processing_pattern']}' pattern were "
                                f"kept and 6) isoforms were removed.{split_text} The output files "
                                f"({nr_files_output_p}) were generated in the '{output_p}' directory.\n")
                    with open(pipsum_ref, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                    with open(pipsum_doi, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "check_contamination":
                    diff = (nr_files_output_p or 0) - (nr_files_input_p or 0)
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and added the {v['check_cont_taxonomy']} taxonomy to the "
                            f"name of each file in the input folder as a suffix using SEDA-CLI ({V('seda')}) "
                            f"operations. The value of this suffix was then compared to the value declared "
                            f"in the config file ({v['check_cont_category']}) and if there was a discrepancy "
                            f"then the file was considered a contaminant.{split_text} The output files were "
                            f"generated in the '{output_p}' directory and {diff} contaminants were found.\n")
                    with open(pipsum_ref, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                    with open(pipsum_doi, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "disambiguate":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and using SEDA-CLI ({V('seda')}) operations, it added an "
                            f"incremental suffix to identical sequence headers. The output files were "
                            f"generated in the '{output_p}' directory.\n")
                    with open(pipsum_ref, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                    with open(pipsum_doi, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "merge":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and merged all of them into a single file and removed "
                            f"redundant identical sequences or sub-sequences. The output file was generated "
                            f"in the '{output_p}' directory.\n")
                elif module == "prefix":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and it added a prefix to the sequence headers. The "
                            f"output files were generated in the '{output_p}' directory.\n")
                elif module == "prefix_out":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and it removed the prefixes that were added by the "
                            f"prefix module. The output files were generated in the '{output_p}' "
                            f"directory.\n")
                elif module == "remove_stops":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and using SEDA-CLI ({V('seda')}) operations, it removed "
                            f"sequences stop codons.{split_text} The output files were generated in the "
                            f"'{output_p}' directory.\n")
                    with open(pipsum_ref, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                    with open(pipsum_doi, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "species_list":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory (sequence headers starts with the organism name) and "
                            f"returned as output a list with the names of all the unique species present in "
                            f"the headers of the input files and also a list with the total counts of how "
                            f"many times each species appear in the input files headers.{split_text} The "
                            f"output files were generated in the '{output_p}' directory.\n")
                elif module == "species_list_genomes":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and returned as output a list with the names of all the "
                            f"unique species present in the input files genomes and also a list with the "
                            f"total counts of how many times each species appear in the input files."
                            f"{split_text} The output files were generated in the '{output_p}' directory.\n")

                # ALIGNMENT Modules

                if module == "Clustal_Omega":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide FASTA file from "
                                f"the '{input_p}' directory with {num_sequences} sequences. SEDA-CLI "
                                f"({V('seda')}) operations were performed to remove line breaks from "
                                f"sequences. Using the Clustal Omega ({V('clustalomega')}) program, a single "
                                f"sequence alignment FASTA file was created. The output file was generated "
                                f"in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'Clustal Omega: "{v["clustalomega_doi"]}", "{v["clustalomega_ref"]}"\n')
                            pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'Clustal Omega: "{v["clustalomega_ref"]}", "{v["clustalomega_doi"]}"\n')
                            pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "Clustal_Omega_codons":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single CDS FASTA file (sequences "
                                f"without stop codons) from the '{input_p}' directory with {num_sequences} "
                                f"sequences. The provided nucleotide sequences were first translated into "
                                f"amino acid sequences using the EMBOSS transeq feature ({V('emboss')}), and "
                                f"an amino acid alignment was obtained using Clustal Omega "
                                f"({V('clustalomega')}). Then, the corresponding nucleotide alignment was "
                                f"obtained using TranslatorX ({V('translatorx')}). The output file was "
                                f"generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_doi"]}", "{v["emboss_ref"]}"\n')
                            pf.write(f'Clustal Omega: "{v["clustalomega_doi"]}", "{v["clustalomega_ref"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_doi"]}", "{v["translatorx_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_ref"]}, "{v["emboss_doi"]}"\n')
                            pf.write(f'Clustal Omega: "{v["clustalomega_ref"]}", "{v["clustalomega_doi"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_ref"]}", "{v["translatorx_doi"]}"\n')
                elif module == "Mafft":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide FASTA file from "
                                f"the '{input_p}' directory with {num_sequences} sequences and using the "
                                f"MAFFT ({V('mafft')}) program, returned as output a single sequence "
                                f"alignment FASTA file. Additionally, SEDA-CLI ({V('seda')}) operations were "
                                f"performed in order to remove line breaks from the resulting alignment. "
                                f"The output file was generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'MAFFT: "{v["mafft_doi"]}", "{v["mafft_ref"]}"\n')
                            pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'MAFFT: "{v["mafft_ref"]}", "{v["mafft_doi"]}"\n')
                            pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "Mafft_codons":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single CDS FASTA file (sequences "
                                f"without stop codons) from the '{input_p}' directory with {num_sequences} "
                                f"sequences and the provided nucleotide sequences were first translated "
                                f"into amino acid sequences using the EMBOSS transeq feature ({V('emboss')}), "
                                f"and an amino acid alignment was obtained using MAFFT ({V('mafft')}). Then, "
                                f"the corresponding nucleotide alignment was obtained using TranslatorX "
                                f"({V('translatorx')}). Additionally, SEDA-CLI ({V('seda')}) operations were "
                                f"performed in order to remove line breaks from the resulting alignment. The "
                                f"output file was generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_doi"]}", "{v["emboss_ref"]}"\n')
                            pf.write(f'MAFFT: "{v["mafft_doi"]}", "{v["mafft_ref"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_doi"]}", "{v["translatorx_ref"]}"\n')
                            pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_ref"]}", "{v["emboss_doi"]}"\n')
                            pf.write(f'MAFFT: "{v["mafft_ref"]}", "{v["mafft_doi"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_ref"]}, "{v["translatorx_doi"]}"\n')
                            pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "Probcons":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide FASTA file from "
                                f"the '{input_p}' directory with {num_sequences} sequences and using the "
                                f"PROBCONS ({V('probcons')}) program, returned as output a single sequence "
                                f"alignment FASTA file. Additionally, SEDA-CLI ({V('seda')}) operations were "
                                f"performed in order to reformat files. The output file was generated in the "
                                f"'{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'ProbCons: "{v["probcons_doi"]}", "{v["probcons_ref"]}"\n')
                            pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'ProbCons: "{v["probcons_ref"]}", "{v["probcons_doi"]}"\n')
                            pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "Probcons_codons":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single CDS FASTA file (sequences "
                                f"without stop codons) from the '{input_p}' directory with {num_sequences} "
                                f"sequences and the provided nucleotide sequences were first translated into "
                                f"amino acid sequences using the EMBOSS transeq feature ({V('emboss')}), and "
                                f"an amino acid alignment was obtained using PROBCONS ({V('probcons')}). "
                                f"Then, the corresponding nucleotide alignment was obtained using TranslatorX "
                                f"({V('translatorx')}). Additionally, SEDA-CLI ({V('seda')}) operations were "
                                f"performed in order to reformat files. The output file was generated in the "
                                f"'{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_doi"]}", "{v["emboss_ref"]}"\n')
                            pf.write(f'ProbCons: "{v["probcons_doi"]}", "{v["probcons_ref"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_doi"]}", "{v["translatorx_ref"]}"\n')
                            pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_ref"]}", "{v["emboss_doi"]}"\n')
                            pf.write(f'ProbCons: "{v["probcons_ref"]}", "{v["probcons_doi"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_ref"]}", "{v["translatorx_doi"]}"\n')
                            pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')
                elif module == "Probcons_refinement":
                    aligned_files = sorted(glob.glob(f"{input_dir_path}/*aligned"))
                    if aligned_files:
                        file_name = os.path.basename(aligned_files[0])
                        path = f"{input_dir_path}/{file_name}"
                        if os.path.isfile(path):
                            num_sequences = count_headers(path)
                            f.write(f"The {module} module accepted as input a single FASTA file from the "
                                    f"'{input_p}' directory containing {num_sequences} aligned sequences and "
                                    f"using the PROBCONS ({V('probcons')}) program refinement option with "
                                    f"{v['probcons_refin_iterations']} iterations, returned a refined FASTA "
                                    f"file. The output file was generated in the '{output_p}' directory.\n")
                            with open(pipsum_ref, "a") as pf:
                                pf.write(f'ProbCons: "{v["probcons_doi"]}", "{v["probcons_ref"]}"\n')
                            with open(pipsum_doi, "a") as pf:
                                pf.write(f'ProbCons: "{v["probcons_ref"]}, "{v["probcons_doi"]}"\n')
                elif module == "T-coffee":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide FASTA file from "
                                f"the '{input_p}' directory with {num_sequences} sequences and using the "
                                f"T-Coffee ({V('tcoffee')}) program, returned as output a single sequence "
                                f"alignment FASTA file. The output file was generated in the '{output_p}' "
                                f"directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'T-Coffee: "{v["tcoffee_doi"]}", "{v["tcoffee_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'T-Coffee: "{v["tcoffee_ref"]}", "{v["tcoffee_doi"]}"\n')
                elif module == "T-coffee_codons":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single CDS FASTA file (sequences "
                                f"without stop codons) from the '{input_p}' directory with {num_sequences} "
                                f"sequences and the provided nucleotide sequences were first translated into "
                                f"amino acid sequences using the EMBOSS transeq feature ({V('emboss')}), and "
                                f"an amino acid alignment was obtained using T-Coffee ({V('tcoffee')}). Then, "
                                f"the corresponding nucleotide alignment was obtained using TranslatorX "
                                f"({V('translatorx')}). The output file was generated in the '{output_p}' "
                                f"directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_doi"]}", "{v["emboss_ref"]}"\n')
                            pf.write(f'T-Coffee: "{v["tcoffee_doi"]}", "{v["tcoffee_ref"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_doi"]}", "{v["translatorx_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_ref"]}", "{v["emboss_doi"]}"\n')
                            pf.write(f'T-Coffee: "{v["tcoffee_ref"]}", "{v["tcoffee_doi"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_ref"]}", "{v["translatorx_doi"]}"\n')
                elif module == "Muscle":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide FASTA file from "
                                f"the '{input_p}' directory with {num_sequences} sequences and using the "
                                f"MUSCLE ({V('muscle')}) program, returned as output a single sequence "
                                f"alignment FASTA file. The output file was generated in the '{output_p}' "
                                f"directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'MUSCLE: "{v["muscle_doi"]}", "{v["muscle_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'MUSCLE: "{v["muscle_ref"]}", "{v["muscle_doi"]}"\n')
                elif module == "Muscle_codons":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single CDS FASTA file (sequences "
                                f"without stop codons) from the '{input_p}' directory with {num_sequences} "
                                f"sequences and the provided nucleotide sequences were first translated into "
                                f"amino acid sequences using the EMBOSS transeq feature ({V('emboss')}), and "
                                f"an amino acid alignment was obtained using MUSCLE ({V('muscle')}). Then, "
                                f"the corresponding nucleotide alignment was obtained using TranslatorX "
                                f"({V('translatorx')}). The output file was generated in the '{output_p}' "
                                f"directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_doi"]}", "{v["emboss_ref"]}"\n')
                            pf.write(f'MUSCLE: "{v["muscle_doi"]}", "{v["muscle_ref"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_doi"]}", "{v["translatorx_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'EMBOSS: "{v["emboss_ref"]}", "{v["emboss_doi"]}"\n')
                            pf.write(f'MUSCLE: "{v["muscle_ref"]}", "{v["muscle_doi"]}"\n')
                            pf.write(f'TranslatorX: "{v["translatorx_ref"]}", "{v["translatorx_doi"]}"\n')

                # TREE BUILDING Modules

                if module == "get_phylo_taxa":
                    file_name = sorted(os.listdir(output_dir_path))[0]
                    path = f"{output_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module was used to extract from the input Newick tree in the "
                                f"'{input_p}' directory, all the taxa located in a given clade (delimited by "
                                f"'{v['get_phylo_taxa_name1']}' and '{v['get_phylo_taxa_name1']}') producing "
                                f"as output an unaligned FASTA file containing {num_sequences} nucleotide "
                                f"sequences. Additionally, SEDA-CLI ({V('seda')}) operations were performed "
                                f"in order to reformat files. The output file was generated in the "
                                f"'{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'SEDA: "{v["seda_ref"]}, "{v["seda_doi"]}"\n')
                elif module == "Fasttree":
                    aligned_files = sorted(glob.glob(f"{input_dir_path}/*aligned"))
                    if aligned_files:
                        file_name = os.path.basename(aligned_files[0])
                        path = f"{input_dir_path}/{file_name}"
                        if os.path.isfile(path):
                            num_sequences = count_headers(path)
                            f.write(f"The {module} module accepted as input a single nucleotide sequence "
                                    f"alignment FASTA file from the '{input_p}' directory with "
                                    f"{num_sequences} sequences and using the Fasttree ({V('fasttree')}) "
                                    f"program it applied a generalized time-reversible model of nucleotide "
                                    f"evolution with a proportion of invariant sites and a gamma distribution "
                                    f"(GTR+I+G), returning as output a tree in Newick format. The output file "
                                    f"was generated in the '{output_p}' directory.\n")
                            with open(pipsum_ref, "a") as pf:
                                pf.write(f'FastTree: "{v["fasttree_doi"]}", "{v["fasttree_ref"]}"\n')
                            with open(pipsum_doi, "a") as pf:
                                pf.write(f'FastTree: "{v["fasttree_ref"]}", "{v["fasttree_doi"]}"\n')
                elif module == "Fastroot":
                    rooting_method = {"MV": "Minimum Variance Rooting", "MP": "Midpoint Rooting"}.get(
                        v["fastroot_rooting_method"], "Outgroup Rooting")
                    f.write(f"The {module} module accepted as input one Newick tree file from the "
                            f"'{input_p}' directory and using the FastRoot ({V('fastroot')}) program it "
                            f"rooted the tree using the {v['fastroot_rooting_method']} ({rooting_method}), "
                            f"returning as output a rooted tree in Newick format. The output file was "
                            f"generated in the '{output_p}' directory.\n")
                    with open(pipsum_ref, "a") as pf:
                        pf.write(f'FastRoot: "{v["fastroot_doi"]}", "{v["fastroot_ref"]}"\n')
                    with open(pipsum_doi, "a") as pf:
                        pf.write(f'FastRoot: "{v["fastroot_ref"]}", "{v["fastroot_doi"]}"\n')
                elif module == "me_tree":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide alignment in "
                                f"FASTA format from the '{input_p}' directory with {num_sequences} sequences "
                                f"and using the MegaX_CC ({V('megaxcc')}) program it returned a minimum "
                                f"evolution tree in Newick format using {v['me_tree_bootstrap']} bootstraps "
                                f"and the {v['me_tree_treatment']} option to treat the sites with alignment "
                                f"gaps. The output file was generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_doi"]}", "{v["megaxcc_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_ref"]}", "{v["megaxcc_doi"]}"\n')
                elif module == "ml_tree":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide alignment in "
                                f"FASTA format from the '{input_p}' directory with {num_sequences} sequences "
                                f"and using the MegaX_CC ({V('megaxcc')}) program it returned a maximum "
                                f"likelihood tree in Newick format using {v['ml_tree_bootstrap']} bootstraps "
                                f"and the {v['ml_tree_treatment']} option to treat the sites with alignment "
                                f"gaps. The output file was generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_doi"]}", "{v["megaxcc_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_ref"]}", "{v["megaxcc_doi"]}"\n')
                elif module == "mp_tree":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide alignment in "
                                f"FASTA format from the '{input_p}' directory with {num_sequences} sequences "
                                f"and using the MegaX_CC ({V('megaxcc')}) program it returned a maximum "
                                f"parsimony tree in Newick format using {v['mp_tree_bootstrap']} bootstraps "
                                f"and the {v['mp_tree_treatment']} option to treat the sites with alignment "
                                f"gaps. The output file was generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_doi"]}", "{v["megaxcc_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'MegaX_CC: {v["megaxcc_ref"]}, {v["megaxcc_doi"]}\n')
                elif module == "nj_tree":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide alignment in "
                                f"FASTA format from the '{input_p}' directory with {num_sequences} sequences "
                                f"and using the MegaX_CC ({V('megaxcc')}) program it returned a "
                                f"neighbor-joining tree in Newick format using {v['nj_tree_bootstrap']} "
                                f"bootstraps and the {v['nj_tree_treatment']} option to treat the sites with "
                                f"alignment gaps. The output file was generated in the '{output_p}' "
                                f"directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_doi"]}", "{v["megaxcc_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_ref"]}", "{v["megaxcc_doi"]}"\n')
                elif module == "upgma_tree":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single nucleotide alignment in "
                                f"FASTA format from the '{input_p}' directory with {num_sequences} sequences "
                                f"and using the MegaX_CC ({V('megaxcc')}) program it returned an upgma tree "
                                f"in Newick format using {v['upgma_tree_bootstrap']} bootstraps and the "
                                f"{v['upgma_tree_treatment']} option to treat the sites with alignment gaps. "
                                f"The output file was generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_doi"]}", "{v["megaxcc_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'MegaX_CC: "{v["megaxcc_ref"]}", "{v["megaxcc_doi"]}"\n')
                elif module == "MrBayes":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single CDS alignment FASTA file "
                                f"from the '{input_p}' directory with {num_sequences} sequences and using "
                                f"the MrBayes ({V('mrbayes')}) program it returned a tree in Newick format "
                                f"implemented using a generalized time-reversible model of nucleotide "
                                f"evolution with a proportion of invariant sites and an independent gamma "
                                f"distribution for first/second and third codon sites (GTR+I+G). The tree "
                                f"was produced using {v['mb_ngen']} generations and a burnin value of "
                                f"{v['mb_burnin']}. Please check the MrBayes log file in the 'files_to_keep' "
                                f"folder to see if convergence has been achieved (the final average standard "
                                f"deviation of split frequencies value should be smaller than 0.01 or PSRF "
                                f"values should approach 1.0 as runs converge). The output file was generated "
                                f"in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'MrBayes: "{v["mrbayes_doi"]}", "{v["mrbayes_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'MrBayes: "{v["mrbayes_ref"]}", "{v["mrbayes_doi"]}"\n')
                elif module == "raxml":
                    aligned_files = sorted(glob.glob(f"{input_dir_path}/*aligned"))
                    if aligned_files:
                        file_name = os.path.basename(aligned_files[0])
                        path = f"{input_dir_path}/{file_name}"
                        if os.path.isfile(path):
                            num_sequences = count_headers(path)
                            f.write(f"The {module} module accepted as input a single nucleotide alignment in "
                                    f"FASTA format from the '{input_p}' directory with {num_sequences} "
                                    f"sequences and using the RaxML ({V('raxml')}) program it implemented a "
                                    f"GTRGAMMAI model, returning as output a maximum likelihood phylogenetic "
                                    f"tree in Newick format. The output file was generated in the "
                                    f"'{output_p}' directory.\n")
                            with open(pipsum_ref, "a") as pf:
                                pf.write(f'RaxML: "{v["raxml_doi"]}", "{v["raxml_ref"]}"\n')
                            with open(pipsum_doi, "a") as pf:
                                pf.write(f'RaxML: "{v["raxml_ref"]}", "{v["raxml_doi"]}"\n')
                elif module == "Rootdigger":
                    aligned_files = sorted(glob.glob(f"{input_dir_path}/*aligned"))
                    if aligned_files:
                        file_name = os.path.basename(aligned_files[0])
                        path = f"{input_dir_path}/{file_name}"
                        if os.path.isfile(path):
                            num_sequences = count_headers(path)
                            f.write(f"The {module} module accepted as input a nucleotide alignment file in "
                                    f"FASTA format from the '{input_p}' directory with {num_sequences} "
                                    f"sequences as well as a Newick tree file with the corresponding tree "
                                    f"and using the Root Digger ({V('rootdigger')}) program it produced a "
                                    f"rooted tree with the {v['rootdigger_mode']} Root Digger mode. The "
                                    f"output file was generated in the '{output_p}' directory.\n")
                            with open(pipsum_ref, "a") as pf:
                                pf.write(f'Root Digger: "{v["rootdigger_doi"]}", "{v["rootdigger_ref"]}"\n')
                            with open(pipsum_doi, "a") as pf:
                                pf.write(f'Root Digger: "{v["rootdigger_ref"]}", "{v["rootdigger_doi"]}"\n')
                elif module == "view_trees":
                    if v["vt_show_branch_length"] == "y":
                        f.write(f"The {module} module accepted as input a Newick tree file from the "
                                f"'{input_p}' directory and using the Newick Utilities "
                                f"({V('newick_utils')}) program it returned an SVG file containing the "
                                f"phylogenetic tree representation showing the branch lenghts with a "
                                f"{v['vt_support_cutoff']} minimum support value and a "
                                f"{v['vt_show_branch_length']} branch length value. The output file was "
                                f"generated in the '{output_p}' directory.\n")
                    else:
                        f.write(f"The {module} module accepted as input a Newick tree file from the "
                                f"'{input_p}' directory and using the Newick Utilities "
                                f"({V('newick_utils')}) program it returned an SVG file containing the "
                                f"phylogenetic tree representation with a {v['vt_support_cutoff']} minimum "
                                f"support value. The output file was generated in the '{output_p}' "
                                f"directory.\n")
                    with open(pipsum_ref, "a") as pf:
                        pf.write(f'Newick Utilities: "{v["newick_utils_doi"]}", "{v["newick_utils_ref"]}"\n')
                    with open(pipsum_doi, "a") as pf:
                        pf.write(f'Newick Utilities: "{v["newick_utils_ref"]}", "{v["newick_utils_doi"]}"\n')
                elif module == "tree_collapse":
                    f.write(f"The {module} module accepted as input a Newick tree file from the '{input_p}' "
                            f"directory and using the Phylogenetic Tree Collapser program it returned a "
                            f"collapsed Newick tree. The output file was generated in the '{output_p}' "
                            f"directory.\n")

                # MODEL CHECKING Modules

                if module == "JModel_test":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a nucleotide alignment in FASTA "
                                f"format from the '{input_p}' directory with {num_sequences} sequences and "
                                f"using the JModel test program ({V('jmodeltest')}) it produced a report to "
                                f"check whether the GTR+I+G model used by the Fasttree and MrBayes modules "
                                f"is appropriate. The output file was generated in the '{output_p}' "
                                f"directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'JModel test: "{v["jmodeltest_doi"]}", "{v["jmodeltest_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'JModel test: "{v["jmodeltest_ref"]}", "{v["jmodeltest_doi"]}"\n')

                # GENE ANNOTATION Modules

                if module == "CGA":
                    if v["cga_selection_criterion"] == "1":
                        criterion_text = ("similarity with reference sequence first, in case of a tie, "
                                           "percentage of gaps relative to reference sequence")
                    elif v["cga_selection_criterion"] == "2":
                        criterion_text = ("percentage of gaps relative to reference sequence first, in "
                                           "case of a tie, similarity with reference sequence")
                    else:
                        criterion_text = (f"mixed model with similarity with reference sequence first, but "
                                           f"if fewer gaps relative to reference sequence, similarity gets a "
                                           f"{v['cga_selection_correction']}% selection bonus correction")
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and implemented the following steps: 1) a tblastn with a "
                            f"{v['cga_expect1']} expect value, that using one or more protein sequences "
                            f"returns a FASTA file for each input file and protein used as query, containing "
                            f"all Blast hit regions plus a {v['cga_hit_region_window1']} number of bases "
                            f"window around the hits; 2) a grow sequences step as implemented in SEDA-CLI "
                            f"({V('seda')}) in order to merge sequences in the same file that show at least "
                            f"a {v['cga_min_overlap']} bases overlap; 3) then, the CGA pipeline "
                            f"(https://hub.docker.com/r/pegi3s/cga/) was used to perform CDS annotations, "
                            f"using as reference a single amino acid sequence. On this module, the "
                            f"parameters defined were: a {v['cga_max_dist']} bases maximum distance between "
                            f"exons from the same gene, a  {v['cga_intron_bp']} bases distance around the "
                            f"junction point between two sequences where to look for splicing signals, a "
                            f"{v['cga_min_full_nucleotide_size']} bases minimum size for reporting CDS and a "
                            f"selection model that was used based on a {criterion_text}. The output files "
                            f"({nr_files_output_p}) were generated in the '{output_p}' directory.\n")
                    with open(pipsum_ref, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_doi"]}", "{v["seda_ref"]}"\n')
                    with open(pipsum_doi, "a") as pf:
                        pf.write(f'SEDA: "{v["seda_ref"]}", "{v["seda_doi"]}"\n')

                # DETECTION OF POSITIVELY SELECTED AMINO ACID SITES Modules

                if module == "ipssa":
                    # NOTE: mirrors the original script, which describes IPSSA's fixed defaults here
                    # rather than the actual config values used at runtime
                    ipssa_sequence_limit = "90"
                    ipssa_align_method = "muscle"
                    ipssa_tcoffee_min_score = "3"
                    ipssa_mrbayes_generations = "1000000"
                    ipssa_mrbayes_burnin = "2500"
                    ipssa_fubar_sequence_limit = "90"
                    ipssa_fubar_runs = "1"
                    ipssa_codeml_sequence_limit = "30"
                    ipssa_codeml_runs = "1"
                    ipssa_codeml_models = "1, 2, 7 and 8"
                    ipssa_omegamap_sequence_limit = "90"
                    ipssa_omegamap_iterations = "2500"

                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input one CDS FASTA file with "
                                f"{num_sequences} sequences from the '{input_p}' directory and IPSSA "
                                f"({V('ipssa')}) was used to automatically identify positively selected "
                                f"amino acid sites and check if there is evidence for recombination in the "
                                f"sequence data using PhiPack, returning as output a tabular formatted file "
                                f"containing the results of all selected PSS methods. The parameters used in "
                                f"this module were: maximum number of sequence to use for the master file "
                                f"was {ipssa_sequence_limit}, the random seed used was "
                                f"{v['ipssa_random_seed']}, the alignment method used was "
                                f"{ipssa_align_method}, the minimum support value for alignment positions "
                                f"was {ipssa_tcoffee_min_score}, the number of iterations in MrBayes was "
                                f"{ipssa_mrbayes_generations} and the burnin value was "
                                f"{ipssa_mrbayes_burnin}, the maximum number of sequence to be used by FUBAR "
                                f"was {ipssa_fubar_sequence_limit} and the number of independent replicas "
                                f"used by FUBAR was {ipssa_fubar_runs}, the maximum number of sequence to be "
                                f"used by CodeML was {ipssa_codeml_sequence_limit}, the number of "
                                f"independent replicas was {ipssa_codeml_runs} and the CodeML models used "
                                f"were {ipssa_codeml_models}, the maximum number of sequences to be used by "
                                f"omegaMap was {ipssa_omegamap_sequence_limit}, the number of omegaMap "
                                f"iterations was {ipssa_omegamap_iterations} and the number of independent "
                                f"replicas was {v['ipssa_omegamap_runs']}. The output file were generated in "
                                f"the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'ipssa: "{v["ipssa_doi"]}", "{v["ipssa_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'ipssa: "{v["ipssa_ref"]}", "{v["ipssa_doi"]}"\n')

                # RECOMBINATION

                if module == "phipack":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input a single aligned FASTA file from "
                                f"the '{input_p}' directory with {num_sequences} sequences and using the "
                                f"PhiPack software ({V('phipack')}) it implemented tests for recombination "
                                f"(Pairwise Homoplasy Index (Phi), Maximum \u03c7\u00b2 (Max Chi\u00b2) and the Neighbour "
                                f"Similarity Score (NSS)) with {v['phipack_permutations']} permutations, "
                                f"returning as output a file containing the p-values for each test. The "
                                f"output files was generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'PhiPack: "{v["phipack_doi"]}", "{v["phipack_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'PhiPack: "{v["phipack_ref"]}", "{v["phipack_doi"]}"\n')

                # DIVERGENCE ESTIMATES Modules

                if module == "kaks":
                    file_name = sorted(os.listdir(input_dir_path))[0]
                    path = f"{input_dir_path}/{file_name}"
                    if os.path.isfile(path):
                        num_sequences = count_headers(path)
                        f.write(f"The {module} module accepted as input one FASTA file from the '{input_p}' "
                                f"directory containing {num_sequences} CDS sequences and using the KaKs "
                                f"calculator ({V('kaks')}) program, it calculated nonsynonymous (Ka) and "
                                f"synonymous (Ks) substitution rates by using the {v['kaks_model']} model "
                                f"and returned as output a tabular formatted file containing nonsynonymous "
                                f"and synonymous substitution rates, as well as other additional information. "
                                f"The output files were generated in the '{output_p}' directory.\n")
                        with open(pipsum_ref, "a") as pf:
                            pf.write(f'KaKs Calculator: "{v["kaks_doi"]}", "{v["kaks_ref"]}"\n')
                        with open(pipsum_doi, "a") as pf:
                            pf.write(f'KaKs Calculator: "{v["kaks_ref"]}", "{v["kaks_doi"]}"\n')

                # Additional Modules

                if module == "data_summary":
                    f.write(f"The {module} module accepted as input {nr_files_input_p} FASTA files from the "
                            f"'{input_p}' directory and returned as output one text file containing all the "
                            f"unique species present in the input files followed by "
                            f"{v['data_summary_taxonomy']} taxonomy and also a text file with the counts of "
                            f"each species in the specified taxonomy. The output files were generated in the "
                            f"'{output_p}' directory.\n")
                elif module == "copy_data_summary":
                    f.write(f"The {module} module accepted as input the species list text file generated by "
                            f"the 'data_summary' module in the '{input_p}' directory and copied it to the "
                            f"'{output_p}' directory.\n")
                elif module == "compare_data_summary":
                    f.write(f"The {module} module accepted as input two species lists from the '{input_p}' "
                            f"directory and compared them, generating as output three text files: one with "
                            f"the common species between both lists, one with the different species between "
                            f"both lists and the last one with the summary of both. The output files were "
                            f"generated in the '{output_p}' directory.\n")
                elif module == "compare_accessions":
                    f.write(f"The {module} module accepted as input two text files containing only "
                            f"accession numbers (one in each line) and compared them, generating as output a "
                            f"text file indicating which of the accessions numbers are common and which are "
                            f"different between both lists. The output file was generated in the "
                            f"'{output_p}' directory.\n")

        with open(summary_file, "a") as f:
            f.write("\n")
            f.write("================================================================================\n")
            f.write("\n")
            f.write("This was the pipeline file used in this auto-phylo run:\n")
            f.write("\n")
            f.write("\n".join(pipeline_lines_raw) + "\n")
            f.write("\n")
            f.write("================================================================================\n")
            f.write("\n")

    process_pipeline("ref")
    process_pipeline("doi")

    for path in (pipsum_ref, pipsum_doi):
        with open(path) as f:
            lines = f.read().splitlines()
        seen = set()
        deduped = []
        for l in lines:
            if l not in seen:
                deduped.append(l)
                seen.add(l)
        with open(path, "w") as f:
            f.write("\n".join(deduped) + ("\n" if deduped else ""))

    with open("/data/files_to_keep/pipeline_summary_ref", "a") as f:
        f.write("References:\n\n")
        with open(pipsum_ref) as pf:
            f.write(pf.read())

    with open("/data/files_to_keep/pipeline_summary_doi", "a") as f:
        f.write("References:\n\n")
        with open(pipsum_doi) as pf:
            f.write(pf.read())


if __name__ == "__main__":
    print("Creating the pipeline summary", flush=True)
    main()

