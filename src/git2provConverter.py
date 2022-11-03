from datetime import datetime
from os import path
import os
import sys
from typing import Dict, Tuple, Set, List
import pygit2
import prov.model as prov
import prov.graph as provg

import re


def convert(giturl: str, serialization: str, repository_path: str, request_url, options, out_file=None):
    """
    The entry point for the git 2 PROV conversion

    @param giturl: The location (either remote or local) of the repository
    @param serialization: The PROV format. Any of json, provn, xml, rdf
    @param repositoryPath: The destination path for the cloned repository
    @param requestUrl:
    @param options:
    @param out_file: The path where the PROV serialization should be written to
    @return:
    """

    repo = clone(giturl, repository_path)

    prov_document = convert_repository_to_prov(
        repo, serialization, request_url, options)

    # If a path for the output file is specified, write PROV to that file. otherwise print to stdout
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(prov_document.serialize(
                format=serialization, indent=2))
    else:
        print(prov_document.serialize(format=serialization, indent=2))


def getPrefixes(urlprefix: str, request_url: str, serialization):
    """

    @param urlprefix:
    @param request_url:
    @param serialization:
    @return:
    """
    prefixes = {urlprefix: request_url + "#", "fullResult": request_url.split(
        "&")[0] + "&serialization=" + serialization + "#"}

    return prefixes


def convert_repository_to_prov(repo: pygit2.Repository, serialization, requestUrl, options):
    """

    @param repo:
    @param serialization:
    @param requestUrl:
    @param options:
    @return:
    """
    # set the corresponding variables according to the options
    if options.get("ignore"):
        ignore = options["ignore"]
    else:
        ignore = []

    # determine a QName for the bundle
    urlprefix = "result"
    prefixes = getPrefixes(urlprefix, requestUrl, serialization)

    prov_document = get_prov_document(prefixes, urlprefix)
    bundle = list(prov_document.bundles)[0]

    files_set, commits_dict = iterate_repository_head(
        repo, short=options["shortHashes"])

    for file in files_set:
        #  Because all identifiers need to be QNames in PROV, and we need valid turtle as well, we need to get rid of the slashes, spaces and dots
        file_entity_identifier = urlprefix + \
            ":file-" + re.sub(r'[\/. ]', "-", file)

        # add file entity to prov
        file_entity = bundle.entity(
            file_entity_identifier, {"prov:label": file})

    for commit in commits_dict:
        commitTuple = (commit, commits_dict[commit])
        update_prov_document(urlprefix, commitTuple, repo, bundle)

    return prov_document


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


def update_prov_document(urlprefix: str, commitTuple: Tuple[pygit2.Oid, List[Tuple[str, str]]], repo: pygit2.Repository,
                         provBundle: prov.ProvBundle):
    """

    @param urlprefix:
    @param commitTuple: The tuple consisting of a pygit2 commit ID and the List of files modified in the commit. 
    The List of files itself is another tuple of filename and modification type
    @param repo:
    @param provBundle:
    @return:
    """

    # The pygit2 Commit object
    commit: pygit2.Commit = repo.get(commitTuple[0])

    # The PROV identifier (includes the commit hash)
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

    # Add the commit activity to the PROV activities
    commit_activity_identifier = urlprefix + ":" + commit_identifier
    commit_activity: prov.ProvActivity = provBundle.activity(
        commit_activity_identifier, commit_time, None, {prov.PROV_LABEL: subject})

    # Check whether agents already exist for author and committer and if not add them to the ProvDocument
    author_agents = provBundle.get_record(urlprefix + ":" + author)
    if len(author_agents) == 0:
        author_agent: prov.ProvAgent = provBundle.agent(
            urlprefix + ":" + author, {prov.PROV_LABEL: author_label})
    else:
        author_agent = author_agents[0]

    committer_agents = provBundle.get_record(urlprefix + ":" + committer)
    if len(committer_agents) == 0:
        committer_agent: prov.ProvAgent = provBundle.agent(
            urlprefix + ":" + committer, {prov.PROV_LABEL: committer_label})
    else:
        committer_agent = committer_agents[0]

    # Add a wasAssociatedWith relation for the current commit activity, the author and the committer
    if author == committer:
        provBundle.wasAssociatedWith(commit_activity, author_agent, other_attributes={
            prov.PROV_ROLE: "author, committer"},
            identifier=commit_activity_identifier + "_" + author + "_assoc")
    else:
        provBundle.wasAssociatedWith(commit_activity,
                                     author_agent, other_attributes={
                                         prov.PROV_ROLE: "author"},
                                     identifier=commit_activity_identifier + "_" + author + "_assoc")
        provBundle.wasAssociatedWith(commit_activity,
                                     committer_agent, other_attributes={
                                         prov.PROV_ROLE: "committer"},
                                     identifier=commit_activity_identifier + "_" + committer + "_assoc")

    # Since we iterate over the files in the tuple list and the parents of the current commit
    # We have to keep a record of which relations have already been recorded in PROV
    derived_done = []
    informed_done = []
    used_done = []
    activity_done = []

    for file in commitTuple[1]:

        file_entity_identifier = "file-" + re.sub(r'[\/. ]', "-", file[0])

        modification_type = file[1]

        # A file that is mentioned in a commit is a specialization of the general file entity
        commit_file_entity_identifier = urlprefix + ":" + \
            file_entity_identifier + "_" + commit_identifier
        # Check if file_commit entity already exists
        if len(provBundle.get_record(commit_file_entity_identifier)) == 0:
            commit_file_entity = provBundle.entity(
                commit_file_entity_identifier)
        else:
            commit_file_entity = provBundle.get_record(
                commit_file_entity_identifier)[0]

        provBundle.specializationOf(
            commit_file_entity, urlprefix + ":" + file_entity_identifier)

        # Authorship of the commit-file is attributed to the author
        provBundle.wasAttributedTo(commit_file_entity, author_agent, other_attributes={
            prov.PROV_ROLE: "authorship"}, identifier=commit_file_entity_identifier + "_" + author + "_attr")

        # The commit activity was started at author time and ended at commit time
        if commit_activity not in activity_done:
            wsb = provBundle.wasStartedBy(
                commit_activity, time=author_time, identifier=commit_activity_identifier + "_start")
            web = provBundle.wasEndedBy(
                commit_activity, time=commit_time, identifier=commit_activity_identifier + "_end")
            activity_done.append(commit_activity)

        # Handle different modification types differently.
        # Distinguish between D: deleted, A: added, and modified
        match modification_type:
            case "D":
                # The file was deleted by this commit
                provBundle.wasInvalidatedBy(
                    commit_file_entity, commit_activity, time=commit_time, identifier=commit_file_entity_identifier + "_inv")
                break

            case "A":
                # The file was added/generated in this commit
                provBundle.wasGeneratedBy(
                    commit_file_entity, commit_activity, time=commit_time, identifier=commit_file_entity_identifier + "_gen")
                break

            case _:
                # The file was modified in this commit
                generation = commit_file_entity_identifier + "_gen"
                generated_entity = provBundle.wasGeneratedBy(
                    commit_file_entity, commit_activity, time=commit_time, identifier=generation)

                for parent in parents:
                    parent_entity_identifier = file_entity_identifier + \
                        "_commit-" + str(parent.short_id)

                    # The commit activity uses the file entity of the parent commit
                    usage = urlprefix + ":" + parent_entity_identifier + \
                        "_" + commit_identifier + "_use"

                    if not (commit_activity, parent_entity_identifier) in used_done:
                        provBundle.used(commit_activity,
                                        entity=urlprefix + ":" + parent_entity_identifier, time=author_time,
                                        identifier=usage)
                        used_done.append(
                            (commit_activity, parent_entity_identifier))

                    """
                    - The newly generated file entity was derived from the file entity in the parent commit
                    - the derivation was done by the commit activity
                    - The generation relation is referenced
                    - As well as the usage relation

                    JSON Example:

                    "result:result:file-mind_map-json_commit-1b524f7_18e5649_der": {
                        "prov:generatedEntity": "result:file-mind_map-json_commit-1b524f7",
                        "prov:usedEntity": "result:file-mind_map-json_commit-18e5649",
                        "prov:activity": "result:commit-1b524f7",
                        "prov:generation": "result:file-mind_map-json_commit-1b524f7_gen",
                        "prov:usage": "result:file-mind_map-json_commit-18e5649_commit-1b524f7_use"
                    }
                    """
                    if not (commit_file_entity, parent_entity_identifier) in derived_done:
                        provBundle.wasDerivedFrom(
                            generatedEntity=commit_file_entity,
                            usedEntity=urlprefix + ":" + parent_entity_identifier,
                            activity=commit_activity,
                            usage=usage,
                            generation=generation,
                            identifier=urlprefix + ":" + commit_file_entity_identifier + "_" + str(parent.short_id) + "_der")
                        derived_done.append(
                            (commit_file_entity, parent_entity_identifier))
                    else:
                        print(derived_done)

                    # The parent commit activity was "informed" by the new commit
                    if not (commit_activity, urlprefix + ":" + "commit-" + str(parent.short_id)) in informed_done:
                        provBundle.wasInformedBy(
                            commit_activity, urlprefix + ":" +
                            "commit-" + str(parent.short_id),
                            identifier=urlprefix + ":" + commit_identifier + "_" + str(parent.short_id) + "_comm")
                        informed_done.append(
                            (commit_activity, urlprefix + ":" + "commit-" + str(parent.short_id)))


def iterate_repository_head(repo: pygit2.Repository, short=False):
    """
    Iterate the given repository from the current head to find all filenames, and all commits plus the files modified by them

    @param repo:
    @param short:
    @return: (files_set, commits_dict) a tuple containing the set of all files that ever existed in the repository, and a dict of all commits and the files that they modified
    """

    files_set = set()
    commits_dict = {}

    latest_commit = repo.head.target

    prev = repo[repo.head.target].parents[0]

    try:
        for commit in repo.walk(latest_commit):

            if short:
                hash = commit.short_id
            else:
                hash = commit.id

            if (prev is not None):
                diff = commit.tree.diff_to_tree(prev.tree)

                for patch in diff:
                    # A, D, or M for added, deleted or modified
                    modification_type = patch.delta.status_char()

                    file = patch.delta.new_file.path

                    files_set.add(file)

                    if commits_dict.get(hash):
                        commits_dict[hash].append((file, modification_type))
                    else:
                        commits_dict[hash] = [(file, modification_type)]

            prev = commit

    except ValueError:
        print("##### START ERROR")
        print(latest_commit)
        print("##### END ERROR")

    return files_set, commits_dict


def iterate_repository(repo, short=False):
    """
    Iterate the given repository to find all filenames, and all commits plus the files modified by them
    @param repo:
    @param short:
    @return: files_set, commits_dict: a tuple containing the set of all files that ever existed in the repository, and a dict of all commits and the files that they modified
    """

    files_set = set()
    commits_dict = {}
    for branch_name in list(repo.branches):
        branch = repo.branches.get(branch_name)

        latest_commit = branch.target
        prev = repo[branch.target].parents[0]
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

                            files_set.add(file)

                            if commits_dict.get(hash):
                                commits_dict[hash].append(
                                    (file, modification_type))
                            else:
                                commits_dict[hash] = [
                                    (file, modification_type)]

                    # if commit.parents:
                    prev = commit
                    # commit = commit.parents[0]
            except ValueError:
                print("##### START ERROR")
                print(branch_name)
                print(branch)
                print(latest_commit)
                print("##### END ERROR")

    return files_set, commits_dict


def clone(giturl: str, repository_path: path):
    """
    Either clones a remote repository to the repositoryPath or loads a local repository and returns a pygit2 Repository

    @param giturl: The url of a remote repository or path to a local repository
    @param repository_path: The directory path for the repository

    @return: The pygit2 Repository
    """

    if (giturl == repository_path) or os.path.exists(repository_path):
        try:
            repo = pygit2.Repository(repository_path)
        except pygit2.GitError as g:
            print(g)
            print(f"pygit2 couldn't load repository {repository_path}")
    else:
        try:
            print(f"# Cloning {giturl} to {repository_path}")
            repo = pygit2.clone_repository(giturl, repository_path)
        except pygit2.GitError as g:
            print(g)
            print(
                f"pygit2 couldn't clone repository {giturl} to {repository_path}")

    return repo


def get_prov_document(prefixes, urlprefix):
    """

    @param prefixes:
    @param urlprefix:
    @return:
    """
    prov_document = prov.ProvDocument()
    prov_document.add_namespace(urlprefix, prefixes[urlprefix])
    prov_document.add_namespace("fullResult", prefixes["fullResult"])

    provBundle = prov_document.bundle(f"{urlprefix}:provenance")

    return prov_document
