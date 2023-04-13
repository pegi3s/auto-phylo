# auto-phylo

This image facilitates the usage of **auto-phylo**, a pipeline maker for phylogenetic studies. 

An online manual is available [here](http://evolution6.i3s.up.pt/static/auto-phylo/docs/index.html)

# Using the auto-phylo image in Linux

You should adapt and run the following command: `docker run --rm -v /your/data/dir:/data -v /var/run/docker.sock:/var/run/docker.sock docker run pegi3s/auto-phylo`

In this command, you should replace `/your/data/dir` to point to the directory that contains the input files of the pipeline. 

Please note that you must have a `pipeline` and a `config` file under `/your/data/dir` in order for the program to work. Detailed instructions are given [in the online manual](http://evolution6.i3s.up.pt/static/auto-phylo/docs/index.html), where the available modules as well as the parameters that must be declared for each module are described in detail.

# Test data

The [online manual](http://evolution6.i3s.up.pt/static/auto-phylo/docs/test_data.html) provides multiple test data examples that can be used to test the program.

# Using the auto-phylo image in Windows

Please note that data must be under the same drive than the Docker Toolbox installation (usually `C:`) and in a folder with write permissions (e.g. `C:/Users/User_name/`).

You should adapt and run the following command: `docker run --rm -v "/c/Users/User_name/dir/":/data -v /var/run/docker.sock:/var/run/docker.sock docker run pegi3s/auto-phylo`
