from multiprocessing import process
import shutil
from subprocess import call
import sys
import os
import tempfile
import time

from src import convert

args = sys.argv

if (len(args)<2 or len(args)>3 ):
    print("usage: git2prov git_url [{PROV-JSON,PROV-O,PROV-XML,SVG}]")
    sys.exit()

gitUrl = args[1]

serialization = args[2] if len(args)>2 else "PROV_JSON"

# if len(args) > 2:
#     serialization = args[2]
# else:
#     serialization = "PROV_JSON"

tempDir = os.path.join(tempfile.gettempdir(), "git2prov", str(os.getpid()))
requestUrl = 'http://localhost/'
options = { "shortHashes": True }

if (os.path.exists(gitUrl)):
    repositoryPath = gitUrl
else:
    repositoryPath = tempDir

def throw(prov, error):
    if(error):
        raise(BaseException)
    print(prov)

if __name__ == "__main__":

    # print("test")
    print(gitUrl)
    print(serialization)
    print(tempDir)
    # throw("test", "error")

    convert(gitUrl, serialization, repositoryPath, requestUrl, options, throw)

    # time.sleep(4)
    # shutil.rmtree(tempDir)
