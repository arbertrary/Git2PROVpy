import imp
from os import path
import pygit2
import prov.model as prov

import shutil

def convert(giturl:str, serialization, repositoryPath, requestUrl, options, callback):
    if ("git@github.com:" in giturl):
        giturl = giturl.replace("git@github.com:", "https://github.com/")

    repoName = giturl.split("/")[-1].removesuffix(".git")
    # print(repoName)


    repo = clone(giturl, repositoryPath)
    iterate_repository(repo)

    # convertRepositoryToProv(repo, serialization, requestUrl, options)

    # def callback1(error):
    #     if (error):
    #         callback(None, error)
    #         # shutil.rmtree(repositoryPath)
            
    #     else:
    #         def callback2(prov, contentType):
    #             callback(prov, None, contentType)
    #             # shutil.rmtree(repositoryPath)
    #         convertRepositoryToProv(repositoryPath, serialization, requestUrl, options, callback2)

    # clone(giturl, repositoryPath, callback1)

    # getProvObject()


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


    # fileList = 

    print("convertRepositoryToProv")

def iterate_tree(tree:pygit2.Tree, fileList:set, prefix:str=""):
    for obj in tree:
        # print(obj.id, obj.type_str, obj.name)
        if (obj.type_str == "blob"):
            fileList.add(prefix+ obj.name)
        else:
            iterate_tree(obj, fileList, prefix=obj.name+"/")
    return fileList
            

def iterate_repository(repo):
    fileSet:set = set()
    print("# ITERATE REPO")
    for branch_name in list(repo.branches):
        branch = repo.branches.get(branch_name)

        latest_commit = branch.target
        # print(type(latest_commit))
        # latest_commit_id = repo.revparse_single(str(latest_commit))
        # print(latest_commit_id)
        if (type(latest_commit) != str):
            try:
                for commit in repo.walk(latest_commit, pygit2.GIT_SORT_TIME):
                    fileList = iterate_tree(commit.tree, fileSet)
            except ValueError:
                print("##### START ERROR")
                print(branch_name)
                print(branch)   
                print(latest_commit)
                print("##### END ERROR")
    print(fileSet)

def clone(giturl:str, repositoryPath:path):
    print("clone")
    try:
        if (giturl == repositoryPath):       
            repo = pygit2.Repository(repositoryPath)
        else:
            repo = pygit2.clone_repository(giturl, repositoryPath)

        # callback(None)
    except Exception as e:
        print(e)
        # callback(e)
    
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

    provBundle.entity("result:file-screenshots")
    # Entity: now:employment-article-v1.html
    # Agent: nowpeople:Bob
    # provObject.agent('result:Bob')

    # provObject.add_bundle(provBundle)

    # print(provObject.serialize(indent=2))
    return provObject



