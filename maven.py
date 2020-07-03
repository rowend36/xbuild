import sys
import xml.dom.minidom as parser
import os
import urllib.request as req
import re
from  xml.parsers.expat import ExpatError
from build_utils import *
path = os.path

def installDependencies(deps):
    for dep in deps:
        installDependency(dep)

def installDependency(dep):
    extension = ""
    pomContent = ""
    try:
        dep['version'] = parseVersion(dep)
    except Exception as e:
        error(e)
        return False

    logstr=getName(dep)
    cache = dependencyToPath(dep)
    if not os.path.exists(cache+".pom"):
        info("Downloading " +logstr)
        try:
            pomContent = download(dependencyToBaseUrl(dep)+".pom",
                cache+".pom")

            extension = getDependencyType(pomContent)
            download(dependencyToBaseUrl(dep)+"."+extension,cache+"."+extension)
            return True
        except Exception as e:
            error(e)
            if os.path.exists(cache+".pom"):
                os.remove(cache+".pom")
            return False

    try:
        pomContent = stropen(cache+".pom")
        extension = getDependencyType(pomContent)
        if not path.exists(cache+"."+extension):
             download(dependencyToBaseUrl(dep)+"."+extension,cache)
    except Exception as e:
        error(e)
        if os.path.exists(cache+".pom"):
            os.remove(cache+".pom")
        return False
    return True

def getMetaData(dep):
    baseUrl =("/".join(dep["groupId"].split(".")))+"/"+dep["artifactId"]+"/maven-metadata.xml"
    metafile = dependencyToBasePath(dep)+"maven-metadata.xml"
    metadata = {}
    metadata["versions"] = []
    try:
        if not path.exists(metafile):
            download(baseUrl,metafile)
        info("Reading metadata  "+metafile)
        meta=parser.parseString(stropen(metafile))
    except ExpatError:
        error("Parse error in "+metafile)
        os.remove(metafile)
        return metadata
    except Exception as e:
        error(e)
        return metadata
    a = meta.getElementsByTagName("version")
    for i in a:
        metadata["versions"].append(i.childNodes[0].data)
    a = meta.getElementsByTagName("latest")
    for i in a:
        metadata["latest"]=i.childNodes[0].data
    a = meta.getElementsByTagName("release")
    for i in a:
        metadata["release"]=i.childNodes[0].data
 
    return metadata

def dependencyToBaseUrl(dep):
    return ("/".join(dep["groupId"].split(".")))+"/"+dep["artifactId"]+"/"+dep["version"]+"/"+dep["artifactId"]+"-"+dep["version"]

def dependencyToBasePath(dep):
     return CACHE_DIR+"/"+("/".join(dep["groupId"].split(".")))+"/"+dep["artifactId"]+"/"

def dependencyToPath(dep):
    return dependencyToBasePath(dep)+dep['version']+"/"+dep["artifactId"]+"-"+dep["version"]

def getDependencyType(pom):
    pomxml = parser.parseString(pom)
    packaging = pomxml.getElementsByTagName("packaging")
    if packaging:
        return packaging[0].childNodes[0].data
    else:
        return "jar"

def getDependenciesFromPom(pom):
    a = parser.parseString(pom)
    deps = a.getElementsByTagName("dependency")
    dependencies = []
    for i in deps:
        item = {}
        scope = i.getElementsByTagName("scope")
        if scope:
            item["scope"]= scope[0].childNodes[0].data
        else:
            item["scope"]=""
        if item["scope"]=="test":
            continue
        item["groupId"] = i.getElementsByTagName("groupId")[0].childNodes[0].data
        item["artifactId"] = i.getElementsByTagName("artifactId")[0].childNodes[0].data
        try:
            item["version"] = i.getElementsByTagName("version")[0].childNodes[0].data
        except:
            item["version"]="+"
       
        type = i.getElementsByTagName("type")
        if type:
            item["type"]=type[0].childNodes[0].data
        else:
            item["type"]="jar"
        dependencies.append(item)
    return dependencies

def listDependencies(dep):
    deps =[]
    pomContent = stropen(dependencyToPath(dep)+".pom")
    try:
        deps = getDependenciesFromPom(pomContent)
    except Exception as e:
        raise Exception("Error in obtaining dependencies for "+getName(dep))
    return deps

def isMatch(version_str,version):
    ## TODO match version ranges [1.0,)
    ## TODO match latest, release 
    stub = '999999999'
    if USE_NAMED_CANDIDATES:
        stub = 'zzzzzzzzzzz'
    start = version_str.replace("+","")
    end = version_str.replace("+",stub)
    if version>=start and version<=end:
        return True
    return False

def isSameArtifact(version_str,version):
    a = version.split(":")
    b = version_str.split(":")
    if a[0] == b[0] and a[1] == b[1]:
        return True
    return False

def parseVersion(dep):
    result = ""
    basePath=dependencyToBasePath(dep)
    if FORCE_USE_LOCAL and path.exists(basePath):
        for i in os.listdir(basePath):
            if not path.exists(path.join(basePath,i,dep["artifactId"]+"-"+i+".pom")):
                continue
            if i > result:
                result = i
                if i>=dep["version"]:
                    break
        if result:
            if result != dep["version"]:
                info(getName(dep) + " version coerced to "+result)
            return result

    if dep["version"].endswith("+"):
        if path.exists(basePath):
            result = ""
            for i in os.listdir(basePath):
                if not path.exists(path.join(basePath,i,dep["artifactId"]+"-"+i+".pom")):
                     continue
                if isMatch(dep["version"],i):
                        if i > result:
                            result = i
            if result:
                #info(getName(dep) + " version bumped to "+result)
                return result

        metadata = getMetaData(dep)
        result = ""
        if(dep["version"]=="+"):
            if metadata["release"]:
                return metadata["release"]
        for i in metadata["versions"]:
            if isMatch(dep["version"],i):
                if i>result:
                    result = i
        if result:
            info(getName(dep) + " version bumped to "+result)
            return result
        raise Exception("Cant'resolve version"+ dep["artifactId"]+":"+dep["version"])
    else:
        return dep["version"]

def download(url,path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    pom=None
    for i in repos:
        try:
            pom = req.urlopen(i+url)
            break
        except Exception as e:
            pass
    if not pom:
        raise Exception(url+" not resolved")
    cachePom = open(path,"wb")
    pomContent = pom.read()
    cachePom.write(pomContent)
    pom.close()
    cachePom.close()
    return pomContent;

def parseDependency(depString):
    dep = depString.split(":")
    item={}
    item["groupId"]=dep[0]
    item["artifactId"]=dep[1]
    if len(dep)>2:
        item["version"]=dep[2]
    else:
        item["version"]="+"
    return item

def getName(dep):
    return dep["groupId"]+":"+dep["artifactId"]+":"+dep["version"]
