import imp
from os import path
from typing import Tuple, Set
import pygit2
import prov.model as prov

import re

import shutil

def convert(giturl:str, serialization, repositoryPath, requestUrl, options, callback):
    if ("git@github.com:" in giturl):
        giturl = giturl.replace("git@github.com:", "https://github.com/")

    repoName = giturl.split("/")[-1].removesuffix(".git")

    repo = clone(giturl, repositoryPath)
    # iterate_repository(repo)

    provObject = convertRepositoryToProv(repo, serialization, requestUrl, options)
    print(provObject.serialize(indent=2))


def getPrefixes(urlprefix:str, requestUrl:str, serialization):
    prefixes = {}
    prefixes[urlprefix] = requestUrl+"#"
    prefixes["fullResult"] = requestUrl.split("&")[0] + "&serialization="+serialization+"#"

    return prefixes

def convertRepositoryToProv(repo:pygit2.Repository, serialization, requestUrl, options):
    # set the corresponding variables according to the options
    if (options.get("ignore")):
        ignore = options["ignore"]
    else:
        ignore = []
   
    # determine a QName for the bundle
    urlprefix = "result"
    prefixes = getPrefixes(urlprefix, requestUrl, serialization)

    provObject = getProvObject()
    bundle = list(provObject.bundles)[0]
    

    fileList = iterate_repository(repo)
    for name in set([x[2] for x in fileList]):
        #  Because all identifiers need to be QNames in PROV, and we need valid turtle as well, we need to get rid of the slashes, spaces and dots
        currentEntity = re.sub(r'[\/. ]',"-", name) 

        # add entity to prov
        bundle.entity(urlprefix+":file-"+currentEntity, {"prov:label":name})

    return provObject

def iterate_tree(tree:pygit2.Tree, fileList:Set[Tuple[pygit2.Oid, str]],commit_id, prefix:str=""):
    for obj in tree:
        if (obj.type_str == "blob"):
            fileList.add((commit_id, obj.id, prefix + obj.name))
        else:
            iterate_tree(obj, fileList,commit_id, prefix=obj.name+"/")
    return fileList

def iterate_repository(repo):
    fileSet:Set[Tuple[pygit2.Oid, str]] = set()
    print("# ITERATE REPO")
    for branch_name in list(repo.branches):
        branch = repo.branches.get(branch_name)

        latest_commit = branch.target

        if (type(latest_commit) != str):
            try:
                for commit in repo.walk(latest_commit, pygit2.GIT_SORT_TIME):
                    fileList = iterate_tree(commit.tree, fileSet, commit.id)
            except ValueError:
                print("##### START ERROR")
                print(branch_name)
                print(branch)   
                print(latest_commit)
                print("##### END ERROR")
    print(fileSet)
    return fileSet

def clone(giturl:str, repositoryPath:path):
    print("clone")
    try:
        if (giturl == repositoryPath):       
            repo = pygit2.Repository(repositoryPath)
        else:
            repo = pygit2.clone_repository(giturl, repositoryPath)

    except Exception as e:
        print(e)
    
    return repo


def getProvObject():
    provObject = prov.ProvDocument()
    # provObject.set_default_namespace("http://localhost")
    provObject.add_namespace("result", "http://localhost")
    provObject.add_namespace("fullResult", "placeholder")

    # provObject.entity("e01")
    # e1 = provObject.entity('result:test.html')

    provBundle = provObject.bundle("result:provenance")
    # altBundle = provObject.bundle("fullResult:provenance")

    # provBundle.entity("result:file-screenshots")
    # Entity: now:employment-article-v1.html
    # Agent: nowpeople:Bob
    # provObject.agent('result:Bob')

    # provObject.add_bundle(provBundle)

    # print(provObject.serialize(indent=2))
    return provObject



