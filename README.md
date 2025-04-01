# auto-phylo

This image facilitates the usage of **auto-phylo**, a pipeline maker for phylogenetic studies.

# Versions

## v3 - July 2024

An online manual is available [here](http://evolution6.i3s.up.pt/static/auto-phylo/v3/docs/).

The latest version is `v3.2.1` (April 2025).

## v2 - October 2023

An online manual is available [here](http://evolution6.i3s.up.pt/static/auto-phylo/v2/docs/).

The latest version is `v2.2.1` (April 2025).

## v1 - April 2023

An online manual is available [here](http://evolution6.i3s.up.pt/static/auto-phylo/v1/docs).

# Using the auto-phylo image in Linux

You should adapt and run the following command: `docker run --rm -v /your/data/dir:/data -v /var/run/docker.sock:/var/run/docker.sock pegi3s/auto-phylo`

In this command, you should replace `/your/data/dir` to point to the directory that contains the input files of the pipeline. 

Please note that you must have a `pipeline` and a `config` file under `/your/data/dir` in order for the program to work. Detailed instructions are given in the online manual, where the available modules, as well as the parameters that must be declared for each module, are described in detail.

# Test data

## v3

Protocols are available that can be used both as inspiration to develop useful and efficient pipelines, as well as test data. By declaring in the first line of the pipeline file "protocol_description" a full list of the available protocols will be produced. By declaring the name of protocols (one per line, starting at the first line) in the pipeline file, the data for the corresponding protocol will be downloaded to the working directory.

## v2

The [online manual](http://evolution6.i3s.up.pt/static/auto-phylo/v2/docs/test_data.html) provides multiple test data examples that can be used to test the program.

# Citing

If you use auto-phylo, please cite these publications:

> H. López-Fernández; M. Pinto; C.P. Vieira; P. Duque; M. Reboiro-Jato; J. Vieira (2023) [Auto-phylo: A Pipeline Maker for Phylogenetic Studies](https://doi.org/10.1007/978-3-031-38079-2_3). 17th International Conference on Practical Applications of Computational Biology & Bioinformatics: PACBB 2023. Guimarães, Portugal. 12 - July
> H. López-Fernández; M. Pinto; C. P. Vieira; P. Duque; M. Reboiro-Jato; J. Vieira (2024) [auto-phylo v2 and auto-phylo-pipeliner: building advanced, flexible, and reusable pipelines for phylogenetic inferences, estimation of variability levels and identification of positively selected amino acid sites](https://doi.org/10.1515/jib-2023-0046). Journal of Integrative Bioinformatics. Volume 21(2), Article Number 20230046. ISSN: 1613-4516 
