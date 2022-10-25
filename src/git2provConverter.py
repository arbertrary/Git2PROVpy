from os import path
import pygit2
import prov.model as prov

import shutil

def convert(giturl:str, serialization, repositoryPath, requestUrl, options, callback):
    if ("git@github.com:" in giturl):
        giturl = giturl.replace("git@github.com:", "https://github.com/")

    repoName = giturl.split("/")[-1].removesuffix(".git")
    print(repoName)


    def callback1(error):
        if (error):
            callback(None, error)
            # shutil.rmtree(repositoryPath)
            
        else:
            def callback2(prov, contentType):
                callback(prov, None, contentType)
                # shutil.rmtree(repositoryPath)
            convertRepositoryToProv(repositoryPath, serialization, requestUrl, options, callback2)

    # clone(giturl, repositoryPath, callback1)

    getProvObject()


def convertRepositoryToProv(repositoryPath, serialization, requestUrl, options, callback):
    print("convertRepositoryToProv")


def clone(giturl:str, repositoryPath:path, callback):
    print("clone")
    try:
        if (giturl == repositoryPath):       
            repo = pygit2.Repository(repositoryPath)
        else:
            repo = pygit2.clone_repository(giturl, repositoryPath)

        callback(None)
    except Exception as e:
        callback(e)


def getProvObject():
    provObject = prov.ProvDocument()
    # provObject.set_default_namespace("http://localhost")
    provObject.add_namespace("result", "http://localhost")

    # provObject.entity("e01")
    # e1 = provObject.entity('result:test.html')

    provBundle = provObject.bundle("result:provenance") 

    # provBundle.set_default_namespace('http://example.org/2/')
    provBundle.entity("result:file-screenshots")
    # Entity: now:employment-article-v1.html
    # Agent: nowpeople:Bob
    # provObject.agent('result:Bob')

    # provObject.add_bundle(provBundle)

    print(provObject.serialize(indent=2))




