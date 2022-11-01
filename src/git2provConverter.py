from datetime import datetime
import imp
from os import path
import sys
from typing import Dict, Tuple, Set, List
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
    

    fileSet, commitDict = iterate_repository(repo, short=True)
    for name in fileSet:
        #  Because all identifiers need to be QNames in PROV, and we need valid turtle as well, we need to get rid of the slashes, spaces and dots
        currentEntity = re.sub(r'[\/. ]',"-", name) 

        # add entity to prov
        bundle.entity(urlprefix+":file-"+currentEntity, {"prov:label":name})
    
    for commit in commitDict:
        # print(commit)
        # print(commitDict[commit])
        commitTuple = (commit, commitDict[commit])
        getCommitObj(urlprefix,  commitTuple, repo, bundle)

    return provObject

def getCommitObj(urlprefix:str, commitTuple: Tuple[pygit2.Oid, List[Tuple[str, str]]], repo:pygit2.Repository, provBundle: prov.ProvBundle):
    commit:pygit2.Commit = repo.get(commitTuple[0])


    id = "commit-" + str(commitTuple[0])
    commit_time =     datetime.fromtimestamp(commit.commit_time)

    parents = commit.parents
    
    author_label = commit.author.name
    author = "user-"+ re.sub(r'[\/. ]',"-", author_label)
    author_time = datetime.fromtimestamp(commit.author.time)
    
    committer_label = commit.committer.name
    committer = "user-" + re.sub(r'[\/. ]',"-", committer_label)
    committer_time = datetime.fromtimestamp(commit.committer.time)

    subject = commit.message

    # Add the commit activity to the activities
    prov_activity:prov.ProvActivity = provBundle.activity(urlprefix + ":"+ id,commit_time, None, {prov.PROV_LABEL: subject})
    

    # Check whether agents already exist for author and committer and if not add them to the ProvDocument
    author_agents = provBundle.get_record(urlprefix+":"+ author)
    if len(author_agents) == 0:
        author_agent: prov.ProvAgent = provBundle.agent(urlprefix+":"+ author, {prov.PROV_LABEL: author_label})
    else:
        author_agent = author_agents[0]

    committer_agents = provBundle.get_record(urlprefix+":"+ committer)
    
    if len(committer_agents) == 0:
        committer_agent = provBundle.agent(urlprefix+":"+committer, {prov.PROV_LABEL: committer_label})
    else:
        committer_agent = committer_agents[0]

    prov_activity.wasAssociatedWith(author_agent, None, {prov.PROV_ROLE: "author"})
    prov_activity.wasAssociatedWith(committer_agent, None, {prov.PROV_ROLE: "committer"})


    for file in commitTuple[1]:

        entity = "file-"+ re.sub(r'[\/. ]',"-", file[0])
        
        modification_type = file[1]

        # Check if file_commit entity already exists
        if len(provBundle.get_record(urlprefix+":"+entity+"_"+id)) == 0:
            commit_entity = provBundle.entity(urlprefix+":"+entity+"_"+id)
        else:
            commit_entity = provBundle.get_record(urlprefix+":"+entity+"_"+id)[0]

        provBundle.wasAttributedTo(commit_entity, author_agent, None, {prov.PROV_ROLE: "authorship"})

        wsb = provBundle.wasStartedBy(prov_activity, time=commit_time)

        provBundle.specializationOf(commit_entity, urlprefix+":"+entity)

        web = provBundle.wasEndedBy(prov_activity, time=commit_time)

        match modification_type:
            case "D":
                # The file was deleted in this commit
                provBundle.wasInvalidatedBy(commit_entity, prov_activity, time=commit_time)

            case "A":
                # The file was added in this commit
                provBundle.wasGeneratedBy(commit_entity, prov_activity, time=commit_time)            

            case other:
                # The file was modified in this commit
                provBundle.wasGeneratedBy(commit_entity, prov_activity, time=commit_time)
                for parent in parents:
                    parentEntityId = urlprefix+":"+entity+"_"+id +"_commit-"+str(parent.short_id)
                    usage = urlprefix+":"+parentEntityId+"_"+id

                    prov_activity.used(parentEntityId)

                    provBundle.wasDerivedFrom(generatedEntity=commit_entity, usedEntity=parentEntityId, activity=prov_activity)
                    
                    provBundle.wasInformedBy(prov_activity, urlprefix+":"+"commit-"+str(parent.short_id))

        # updateProv(urlprefix, provBundle, commitObject)
   

def updateProv(urlprefix:str, provBundle: prov.ProvBundle, commitObject:Dict):
    # c = provBundle.activity(urlprefix + ":"+ commitObject["id"],commitObject["commit_time"], None, {prov.PROV_LABEL: commitObject["subject"]})

    e = provBundle.entity(urlprefix+":"+commitObject["entity"]+"_"+commitObject["id"])
    wsb = provBundle.wasStartedBy(commitObject["commitActivity"], time=commitObject["commit_time"])

    provBundle.specializationOf(e, urlprefix+":"+commitObject["entity"])

    web = provBundle.wasEndedBy(commitObject["commitActivity"], time=commitObject["commit_time"])
    



# def iterate_tree(tree:pygit2.Tree, fileList:Set[Tuple[pygit2.Oid, str]],commit_id, prefix:str=""):
def iterate_tree(tree:pygit2.Tree, fileDict:Dict,commit_id, prefix:str=""):
    # print(commit_id)
    # if (prefix != ""):
    #     for obj in tree:                 # Iteration
    #         print(obj.id, obj.type_str, obj.name)
    #         # TODO: Why does the "screenshot" tree list ALL screenshot files? Shouldn't it be only one? because only one screenshot is added per commit?
    #  TODO: https://stackoverflow.com/a/28389889
        
    #     return fileDict

    for obj in tree:
        if (obj.type_str == "blob"):
            if (fileDict.get(prefix+obj.name)):
                fileDict[prefix+obj.name].add(obj.id)
            else:
                fileDict[prefix+obj.name] = set([obj.id])
            # fileList.add((commit_id, obj.id, prefix + obj.name))
        else:
            iterate_tree(obj, fileDict,commit_id, prefix=obj.name+"/")
    return fileDict

def iterate_repository(repo, short=False):
    """

    @returns fileSet, commitDict: a tuple containing the set of all files that ever existed in the repository, and a dict of all commits and the files that they modified

    Iterate the given repository to find all filenames, and all commits plus the files modified by them
    """
    # fileSet:Set[Tuple[pygit2.Oid, str]] = set()
    fileDict:Dict = {}
    fileSet = set()
    commitDict = {}
    # print("# ITERATE REPO")
    for branch_name in list(repo.branches):
        branch = repo.branches.get(branch_name)

        latest_commit = branch.target
        prev = None
        if (type(latest_commit) != str):
            try:
                for commit in repo.walk(latest_commit):

                    if short:
                        hash = commit.short_id
                    else:
                        hash = commit.id

                    if (prev is not None):
                        diff = commit.tree.diff_to_tree(prev.tree)
                        # print(diff)
                        
                        for patch in diff:
                            # A, D, or M for added, deleted or modified                           
                            modification_type = patch.delta.status_char()           

                            file = patch.delta.new_file.path

                            fileSet.add(file)
                            

                            
                            if commitDict.get(hash):
                                commitDict[hash].append((file, modification_type))
                            else:
                                commitDict[hash] = [(file, modification_type)]

                    if commit.parents:
                        prev = commit
                        commit = commit.parents[0]
            except ValueError:
                print("##### START ERROR")
                print(branch_name)
                print(branch)   
                print(latest_commit)
                print("##### END ERROR")


    # print(fileSet)
    # print(commitDict)

    return fileSet, commitDict

def clone(giturl:str, repositoryPath:path):
    """
    @param giturl - the url of a remote repository or path to a local repository
    @param repositoryPath - The directory path for the repository

    @returns a pygit2 Repository

    Either clones a remote repository to the repositoryPath or loads a local repository and returns a pygit2 Repository
    """
    # print("clone")
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



