import logging,os

PREFIX=os.getenv("PREFIX")
SIGNING_KEY_PATH = "./main.key"
USE_AAPT2 = False 
ANDROID_JAR = f"{PREFIX}/share/java/android.jar"
#AAPT_ANDROID_JAR = ANDROID_JAR
AAPT_ANDROID_JAR = f"{PREFIX}/share/aapt/android.jar"
DX_JAR_FILE = f"{PREFIX}/share/dex/dx.jar"
AIDL_FRAMEWORK = f"{PREFIX}share/java/framework.aidl"
REQ_PKG=("ecj","dx","aapt","apksigner","zipmerge")
BUILD_APK_PATH ="~/storage/downloads/buildAPKs/"
LIBRARY_PATHS = [".."]
CACHE_DIR="/data/data/com.termux/files/home/lib_cache"
repos =[
        "https://maven.google.com/",
        "https://repo1.maven.org/maven2/",
        "https://jcenter.bintray.com/"
        ]
VERSION_LIMIT = "999999999"
IGNORE_VERSION_CONFLICT=True
USE_NAMED_CANDIDATES = False

#when set to True, maven will use best matching local dependencies even if they are a wrong version
FORCE_USE_LOCAL=False

LOG_LEVEL = logging.DEBUG
#LOG_LEVEL = 1000 #disable logs
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#allow matching of 2.7+ with 2.7-beta etc











##### DO NOT TOUCH UNLESS YOU KNOW WHAT YOU ARE DOING ###
import sys
import re
path = os.path
FIRST = "."
if len(sys.argv)>1:
    FIRST = sys.argv[1]
  
system = os.system
def printer(args):
    debug(args)
    a = system(args)
    if a != 0:
        warn(args.split(" ")[0]+" failed with error code - "+str(a))
    return a
os.system = printer

Logger = logging.getLogger("xbuild")
Logger.setLevel(LOG_LEVEL)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter(LOG_FORMAT)
ch.setFormatter(formatter)
Logger.addHandler(ch)
#print = Logger.info
debug = Logger.debug
info = Logger.info
warn = Logger.warn
error = Logger.error

def wrap(value):
    if not value:
        return []
    if type(value) not in (list,tuple,set):
        value = [value]
    return value

def stropen(filename):
    a = open(filename)
    t = a.read()
    a.close()
    return t

def glob(path_str,glob_,add_folders=False,paths=None,root=None):
    if (paths is None) != (root is None):
        warn(add_folders,paths,root)
        warn("Possible wrong arguments")
    if not path.exists(path_str):
        raise Exception("Path does not exist")
    if paths is None:
        paths=[]
    if root is None:
        root = ""
    regex = re.sub("(\.|\(|\)|\]|\[|\-)","\\\\\\1",glob_)
    regex = regex.replace("*","__STAR__")
    regex = regex.replace("?","__QUES__")
    regex = regex.replace("__STAR____STAR__",".*")
    regex = regex.replace("__STAR__","[^/]*")
    regex = regex.replace("__QUES__","[^/]?")
    regex = "^"+regex+"$"
    for i in os.scandir(path_str):
        if re.match(regex,path.join(root,i.name)):
            if add_folders or not i.is_dir():
                paths.append(i.path)
        if i.is_dir():
            glob(i.path,glob_,add_folders,paths,path.join(root,i.name))
    return paths

def checkSet(iterable):
        checker = []
        for i in iterable:
            if i in checker:
                error("Duplicate entry - "+str(iterable))
                return False
            checker.append(i)
        return True
    
