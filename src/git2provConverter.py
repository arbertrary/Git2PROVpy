from datetime import datetime
import imp
from os import path
import sys
from typing import Dict, Tuple, Set, List
import pygit2
import prov.model as prov

import re

import shutil


def convert(giturl: str, serialization, repositoryPath, requestUrl, options, callback):
    if ("git@github.com:" in giturl):
        giturl = giturl.replace("git@github.com:", "https://github.com/")

    repoName = giturl.split("/")[-1].removesuffix(".git")

    repo = clone(giturl, repositoryPath)
    # iterate_repository(repo)

    provObject = convertRepositoryToProv(
        repo, serialization, requestUrl, options)
    print(provObject.serialize(indent=2))
    # print(provObject.get_provn())


def getPrefixes(urlprefix: str, requestUrl: str, serialization):
    prefixes = {}
    prefixes[urlprefix] = requestUrl+"#"
    prefixes["fullResult"] = requestUrl.split(
        "&")[0] + "&serialization="+serialization+"#"

    return prefixes


def convertRepositoryToProv(repo: pygit2.Repository, serialization, requestUrl, options):
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

    # get_repo_log(repo)
    fileSet, commitDict = get_repo_log(repo, short=True)
    # fileSet, commitDict = iterate_repository_head(repo, short=True)
    for name in fileSet:
        #  Because all identifiers need to be QNames in PROV, and we need valid turtle as well, we need to get rid of the slashes, spaces and dots
        currentEntity = re.sub(r'[\/. ]', "-", name)

        # add entity to prov
        bundle.entity(urlprefix+":file-"+currentEntity, {"prov:label": name})

    for commit in commitDict:
        # print(commit)
        # print(commitDict[commit])
        commitTuple = (commit, commitDict[commit])
        getCommitObj(urlprefix,  commitTuple, repo, bundle)

    return provObject


"""
We convert git concepts to PROV concepts as follows:

  commit c with subject s ---> activity(c, [prov:label="s"])
  file f   ---> entity(f)
  author a ---> agent(a)
               ---> wasAssociatedWith(c, a, [prov:role="author"])
               ---> wasAttributedTo(f_c, a, [prov:type="authorship"])
  committer ca ---> agent(ca)
               ---> wasAssociatedWith(c, ca, [prov:role="committer"])
  author date ad ---> wasStartedBy(c, -, -, ad)
  commit date cd ---> wasEndedBy(c, -, -, cd)
  file f in commit c ---> specializationOf(f_c, f)
  file f_c added in commit c ---> wasGeneratedBy(f_c, c, authordate)
  file f_c in commit c modified f_c2 from parent commit c2
    ---> wasGeneratedBy(f_c, c, authordate)
    ---> used(c, f_c2, authordate)
    ---> wasDerivedFrom(f_c, f_c2, c)
    ---> wasInformedBy(c, c2)
  file f_c deleted in commit c ---> wasInvalidatedBy(f_c, c, authordate)
"""


def getCommitObj(urlprefix: str, commitTuple: Tuple[pygit2.Oid, List[Tuple[str, str]]], repo: pygit2.Repository, provBundle: prov.ProvBundle):
    commit: pygit2.Commit = repo.get(commitTuple[0])

    commit_identifier = "commit-" + str(commitTuple[0])
    commit_time = datetime.fromtimestamp(commit.commit_time)

    parents = commit.parents

    author_label = commit.author.name
    author = "user-" + re.sub(r'[\/. ]', "-", author_label)
    author_time = datetime.fromtimestamp(commit.author.time)

    committer_label = commit.committer.name
    committer = "user-" + re.sub(r'[\/. ]', "-", committer_label)
    committer_time = datetime.fromtimestamp(commit.committer.time)

    subject = commit.message

    # Add the commit activity to the activities
    prov_activity_identifier = urlprefix + ":" + commit_identifier
    prov_activity: prov.ProvActivity = provBundle.activity(
        urlprefix + ":" + commit_identifier, commit_time, None, {prov.PROV_LABEL: subject})

    # Check whether agents already exist for author and committer and if not add them to the ProvDocument
    author_agents = provBundle.get_record(urlprefix+":" + author)
    if len(author_agents) == 0:
        author_agent: prov.ProvAgent = provBundle.agent(
            urlprefix+":" + author, {prov.PROV_LABEL: author_label})
    else:
        author_agent = author_agents[0]

    committer_agents = provBundle.get_record(urlprefix+":" + committer)

    if len(committer_agents) == 0:
        committer_agent = provBundle.agent(
            urlprefix+":"+committer, {prov.PROV_LABEL: committer_label})
    else:
        committer_agent = committer_agents[0]

    if author == committer:
        provBundle.wasAssociatedWith(prov_activity, author_agent, other_attributes={
                                     prov.PROV_ROLE: "author, committer"}, identifier=urlprefix+":"+commit_identifier+"_"+author + "_assoc")
    else:
        provBundle.wasAssociatedWith(prov_activity,
                                     author_agent, other_attributes={prov.PROV_ROLE: "author"}, identifier=urlprefix+":"+commit_identifier+"_"+author + "_assoc")
        provBundle.wasAssociatedWith(prov_activity,
                                     committer_agent, other_attributes={prov.PROV_ROLE: "committer"}, identifier=urlprefix+":"+commit_identifier+"_"+committer + "_assoc")

    derived_done = []
    informed_done = []
    already_used = []

    activity_done = []

    for f in commitTuple[1]:

        file_entity_identifier = "file-" + re.sub(r'[\/. ]', "-", f[0])

        modification_type = f[1]

        commit_entity_identifier = urlprefix+":" + \
            file_entity_identifier+"_"+commit_identifier
        # Check if file_commit entity already exists
        if len(provBundle.get_record(commit_entity_identifier)) == 0:
            commit_entity = provBundle.entity(commit_entity_identifier)
        else:
            commit_entity = provBundle.get_record(
                commit_entity_identifier)[0]

        provBundle.wasAttributedTo(commit_entity, author_agent, other_attributes={
                                   prov.PROV_ROLE: "authorship"}, identifier=commit_entity_identifier+"_"+author+"_attr")

        provBundle.specializationOf(
            commit_entity, urlprefix+":"+file_entity_identifier)

        if prov_activity not in activity_done:
            wsb = provBundle.wasStartedBy(
                prov_activity, time=author_time, identifier=prov_activity_identifier+"_start")
            web = provBundle.wasEndedBy(
                prov_activity, time=commit_time, identifier=prov_activity_identifier+"_end")
            activity_done.append(prov_activity)

        match modification_type:
            case "D":
                # The file was deleted in this commit
                provBundle.wasInvalidatedBy(
                    commit_entity, prov_activity, time=commit_time, identifier=commit_entity_identifier+"_inv")
                break

            case "A":
                # The file was added in this commit
                provBundle.wasGeneratedBy(
                    commit_entity, prov_activity, time=commit_time, identifier=commit_entity_identifier+"_gen")
                break

            case _:
                # The file was modified in this commit
                generation = commit_entity_identifier + "_gen"
                generated_entity = provBundle.wasGeneratedBy(
                    commit_entity, prov_activity, time=commit_time, identifier=generation)

                for parent in parents:
                    # parent_entity_identifier = urlprefix+":"+entity + \
                    #     "_"+commit_identifier + "_commit-"+str(parent.short_id)

                    parent_entity_identifier = file_entity_identifier + \
                        "_commit-"+str(parent.short_id)

                    usage = urlprefix+":" + parent_entity_identifier + "_" + commit_identifier + "_use"

                    if not (prov_activity, parent_entity_identifier) in already_used:
                        provBundle.used(prov_activity,
                                        entity=urlprefix+":" + parent_entity_identifier, time=author_time, identifier=usage)
                        already_used.append(
                            (prov_activity, parent_entity_identifier))

                    if not (commit_entity, parent_entity_identifier) in derived_done:
                        # print(derived_done)
                        provBundle.wasDerivedFrom(
                            generatedEntity=commit_entity,
                            usedEntity=urlprefix+":" + parent_entity_identifier,
                            activity=prov_activity,
                            usage=usage,
                            generation=generation,
                            identifier=urlprefix+":"+commit_entity_identifier+"_"+str(parent.short_id)+"_der")
                        derived_done.append(
                            (commit_entity, parent_entity_identifier))
                    else:
                        print(derived_done)

                    if not (prov_activity, urlprefix+":"+"commit-"+str(parent.short_id)) in informed_done:
                        provBundle.wasInformedBy(
                            prov_activity, urlprefix+":"+"commit-"+str(parent.short_id), identifier=urlprefix+":"+commit_identifier+"_"+str(parent.short_id)+"_comm")
                        informed_done.append(
                            (prov_activity, urlprefix+":"+"commit-"+str(parent.short_id)))

        # updateProv(urlprefix, provBundle, commitObject)


def updateProv(urlprefix: str, provBundle: prov.ProvBundle, commitObject: Dict):
    # c = provBundle.activity(urlprefix + ":"+ commitObject["id"],commitObject["commit_time"], None, {prov.PROV_LABEL: commitObject["subject"]})

    e = provBundle.entity(
        urlprefix+":"+commitObject["entity"]+"_"+commitObject["id"])
    wsb = provBundle.wasStartedBy(
        commitObject["commitActivity"], time=commitObject["commit_time"])

    provBundle.specializationOf(e, urlprefix+":"+commitObject["entity"])

    web = provBundle.wasEndedBy(
        commitObject["commitActivity"], time=commitObject["commit_time"])


def get_repo_log(repo, short=False):
    head = repo.head
    commitDict = {}
    fileSet = set()
    for entry in head.log():

        commit = repo.get(entry.oid_new)
        prev = repo.get(entry.oid_old)

        if short:
            commit_id = commit.short_id
            # prev_id = prev.short_id
        else:
            commit_id = entry.oid_new
            # prev_id = entry.oid_old

        if prev:
            diff = commit.tree.diff_to_tree(prev.tree, swap=True)
        else:
            diff = commit.tree.diff_to_tree(swap=True)

        diffList = []
        for patch in diff:
            # A, D, or M for added, deleted or modified
            modification_type = patch.delta.status_char()

            file = patch.delta.new_file.path

            fileSet.add(file)

            diffList.append((file, modification_type))
            # print(file, modification_type)

        # commitDict[commit_id] = {"parent": prev_id, "diff": diffList}
        commitDict[commit_id] = diffList

    return fileSet, commitDict


def iterate_repository_head(repo, short=False):
    """

    @returns fileSet, commitDict: a tuple containing the set of all files that ever existed in the repository, and a dict of all commits and the files that they modified

    Iterate the given repository to find all filenames, and all commits plus the files modified by them
    """
    # fileSet:Set[Tuple[pygit2.Oid, str]] = set()
    fileDict: Dict = {}
    fileSet = set()
    commitDict = {}
    # print("# ITERATE REPO")
    latest_commit = repo.head.target
    # print(latest_commit)
    prev = repo[repo.head.target].parents[0]
    # if (type(latest_commit) != str):
    try:
        for commit in repo.walk(latest_commit):
            # print(commit)

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
                # commit = commit.parents[0]
    except ValueError:
        print("##### START ERROR")
        print(latest_commit)
        print("##### END ERROR")

    return fileSet, commitDict


def iterate_repository(repo, short=False):
    """

    @returns fileSet, commitDict: a tuple containing the set of all files that ever existed in the repository, and a dict of all commits and the files that they modified

    Iterate the given repository to find all filenames, and all commits plus the files modified by them
    """
    # fileSet:Set[Tuple[pygit2.Oid, str]] = set()
    fileDict: Dict = {}
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
                                commitDict[hash].append(
                                    (file, modification_type))
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


def clone(giturl: str, repositoryPath: path):
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
