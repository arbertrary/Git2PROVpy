from multiprocessing import process
import shutil
from subprocess import call
import sys
import os
import tempfile
import time

import argparse

from src import convert

# args = sys.argv

parser = argparse.ArgumentParser(
    prog="Git2Prov Python", description="Translates a git repository to PROV")
parser.add_argument("gitURI",
                    help="The remote or local URL or path to a git repository. A remote repository will be cloned to "
                         "the destination or the current directory.")
parser.add_argument(
    "-o", "--out", help="The filepath for the PROV output file. If not given print the output to stdout")
parser.add_argument(
    "-d", "--dest", help="Destination of the cloned repository. If none is given, clone to current working directory")
parser.add_argument(
    "-f", "--format", help="The PROV serialization format. Options: json, rdf, provn, or xml. Default: json")
parser.add_argument(
    "--short", help="Whether to use short full git hashes", action="store_true", default=True
)

args = parser.parse_args()

if args.format and args.format in ["json", "rdf", "provn", "xml"]:
    serialization = args.format
else:
    serialization = "json"

# Does the given original local git repository URI exist on the system and is a new clone destination given?
# Then clone repo to new path
if os.path.exists(args.gitURI) and os.path.isdir(args.gitURI) and args.dest:
    repositoryPath = args.dest
    giturl = args.gitURI
# Does the given original local git repository URI exist on the system and nothing else is given?
# Then directly use the repository at the given location
elif os.path.exists(args.gitURI):
    repositoryPath = args.gitURI
    giturl = args.gitURI
else:
    # Is the git URL an ssh URL from github? Then modify it so pygit2 can clone it
    if "git@github.com:" in args.gitURI:
        giturl = args.gitURI.replace("git@github.com:", "https://github.com/")
    # ssh urls of other git providers are not supported yet
    elif "git@" in args.gitURI:
        raise ValueError(
            f"Cloning with an SSH URL is currently only supported for github repositories")
    # Otherwise the giturl is a simple https:// url
    else:
        giturl = args.gitURI

    if args.dest:
        repositoryPath = args.dest
    else:
        repo_name = args.gitURI.split("/")[-1].removesuffix(".git")
        repositoryPath = os.path.join(os.getcwd(), repo_name)


requestUrl = 'http://localhost/'
options = {"shortHashes": args.short}

if __name__ == "__main__":
    if args.out:
        convert(giturl, serialization, repositoryPath,
                requestUrl, options, args.out)
    else:
        convert(giturl, serialization, repositoryPath, requestUrl, options)
