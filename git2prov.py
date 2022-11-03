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
parser.add_argument("gitUri",
                    help="The remote or local URL or path to a git repository. A remote repository will be cloned to the destination or the current directory.")
parser.add_argument(
    "-o", "--out", help="The filepath for the PROV output file")
parser.add_argument(
    "-d", "--dest", help="Destination of the cloned repository. If none is given, clone to current working directory")
parser.add_argument(
    "-f", "--format", help="The PROV serialization format. Options: json, rdf, provn, or xml. Default: json")
parser.add_argument(
    "--short", help="Whether to use short full git hashes", action="store_true", default=True
)

args = parser.parse_args()
# print(type(vars(args)))

if args.format and args.format in ["json", "rdf", "provn", "xml"]:
    serialization = args.format
else:
    serialization = "json"

if os.path.exists(args.gitUri) and os.path.isdir(args.gitUri) and args.dest:
    repositoryPath = args.dest
    giturl = args.gitUri
elif os.path.exists(args.gitUri):
    repositoryPath = args.gitUri
    giturl = args.gitUri
else:
    if "git@github.com:" in args.gitUri:
        giturl = args.gitUri.replace("git@github.com:", "https://github.com/")
    elif "git@" in args.gitUri:
        raise ValueError(
            f"Cloning with an SSH URL is currently only supported for github repositories")

    repoName = args.gitUri.split("/")[-1].removesuffix(".git")
    repositoryPath = os.path.join(os.getcwd(), repoName)


requestUrl = 'http://localhost/'
options = {"shortHashes": args.short}

if __name__ == "__main__":
    if args.out:
        convert(giturl, serialization, repositoryPath,
                requestUrl, options, args.out)
    else:
        convert(giturl, serialization, repositoryPath, requestUrl, options)
