# Git2PROVpy
A Python version of the command line part of the Git2PROV project. https://github.com/IDLabResearch/Git2PROV

## 

This Python command line program uses the [prov library](https://github.com/trungdong/prov)
as well as [pygit2](https://github.com/libgit2/pygit2).

This means the manual PROV serialization done in the original Git2PROV JavaScript code has been replaced by the PROV handling of the `prov` library. The calling of git on the command line from inside the JavaScript code has been replaced by the usage of `pygit2`.


## Limitations

Features of the original Git2PROV code that are not (yet) included are

- The cloning to a temporary directory which is then removed. At least on Windows, trying to remove a git repository e.g. by using `shutil.rmtree` from inside the Python code results in privilege problems.
- This script obviously is only a CLI program and not a web application. It only emulates the [command line version of Git2PROV](https://github.com/IDLabResearch/Git2PROV/blob/master/bin/git2prov)


## Usage

```
usage: Git2Prov Python [-h] [-o OUT] [-d DEST] [-f FORMAT] [--short] gitURI

Translates a git repository to PROV

positional arguments:
  gitURI                The remote or local URL or path to a git repository. A remote repository will be cloned to the destination or the current directory.

options:
  -h, --help            show this help message and exit
  -o OUT, --out OUT     The filepath for the PROV output file. If not given print the output to stdout
  -d DEST, --dest DEST  Destination of the cloned repository. If none is given, clone to current working directory
  -f FORMAT, --format FORMAT
                        The PROV serialization format. Options: json, rdf, provn, or xml. Default: json
  --short               Whether to use short full git hashes
```