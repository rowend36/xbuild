from gradle import parseGradle,parserDefs
import re
from build_utils import *
import maven as mvn
import os.path as path
from manifest import Manifest
class CyclicException(Exception):
    pass
class Dependency():
    globalDeps = {}
    def __init__(self,name):
        super().__init__()
        self.name=name
        self.dependencies=[]
        self.type = 'unresolved'
        self.path = 'unresolved'
        self.collected = False
        self.position = -1
        self.jar_files = []
        self.cyclic = False
        self.options = None
    def getOptions(self):
        return {}
    def addDep(self,dep):
        if dep not in self.dependencies:
            self.dependencies.append(dep)
    def addJars(self,jars):
        self.jar_files.extend(jars)
    def collect(self):
        self.cyclic = True
        try:
            position = 1
            for i in self.dependencies:
                i.collect()
                position+=i.position
            self.position=position
        except CyclicException as e:
            raise CyclicException(self.name+">"+str(e))
        except Exception as f:
            raise f
        finally:
            self.cyclic = False
        self.collected=True
    def getLibs(self,recurse=False):
        paths = list(self.jar_files)
        if recurse:
            for i in self.dependencies:
                for j in i.getLibs(True):
                    if j not in paths:
                        paths.append(j)
        return paths
    def getObjs(self,recurse=False):
        if self.type == "unresolved":
            return []
        if path.exists(self.build_path+"/obj"):
            paths = wrap(self.build_path+"/obj")
        else:
            paths = []
        if recurse:
            for i in self.dependencies:
                for j in i.getObjs(recurse):
                    if j not in paths:
                        paths.append(j)
        return paths
    def getRPath(self):
        if not self.manifest:
            return False
        manifest = Manifest(self.manifest)
        path_=self.build_path+"/gen/"+"/".join(manifest.getPackageName().split("."))+"/R.java"
        if path.exists(path_):
            return path_
        return False
    def getChildRPaths(self):
        paths = []
        a = self.dependencies
        for i in self.dependencies:
            a = i.getRPath()
            if a and a not in paths:
                paths.append(a)
            for j in i.getChildRPaths():
                if j not in paths:
                    paths.append(j)
        return paths
    #def getDexs(self):
    #    if not path.exists(self.dex_path):
    #        return []
    #    paths = wrap(self.dex_path)
    #    return paths

    def listDeps(self,sep="\n"):
        text = ""
        text += self.name
        for i in self.dependencies:
            text += sep+"|--"+i.name
        return text
    def __str__(self):
        return self.listDeps()
  
class ProjectDependency(Dependency):
    def __init__(self,name,path):
        super().__init__(name)
        self.path = path
        self.type = "project"
        self.gradleFile = self.path+"/build.gradle"
        self.options = {}
        Dependency.globalDeps[self.path]=self;
    def getOptions(self):
        return self.options
    def resolvePath(root,name):
        curdir = root
        for i in LIBRARY_PATHS:
            if(path.exists(path.join(curdir,i,name))):
                return path.normpath(path.join(curdir,i,name))
                break
        else:
            raise Exception("Can't find Project "+name)
    def collect(self):
        if self.cyclic:
            raise CyclicException(self.name)
        if self.collected:
            return
        parseGradle(self)
        super().collect()
class JarDependency(Dependency):
    def __init__(self,name,path):
        super().__init__(name)
        self.path = path
        Dependency.globalDeps[self.path]=self
    def collect(self):
        pass
class MvnDependency(Dependency):
    def __init__(self,name,dep=None):
        super().__init__(name)
        self.dep = dep
        Dependency.globalDeps[self.name]=self
    def collect(self):
        if self.cyclic:
            raise CyclicException(self.name)
        if self.collected:
            return
        if not self.dep:
            self.dep = mvn.parseDependency(self.name)
        dep=self.dep;
        if not mvn.installDependency(dep):
            warn(self.name +" not installed")
            return False
        try:
            self.type = mvn.getDependencyType(stropen(mvn.dependencyToPath(dep)+".pom"))
        except Exception as e:
            error(e)
            error("Unable to get type")
            self.type="unresolved"
            return False
        if self.type not in ("aar","jar"):
            warn(f"Unknown dependency type {self.type} for {self.name}")
        self.path = mvn.dependencyToPath(dep)+"."+self.type
        if self.type =="aar":
            self.projectPath = mvn.dependencyToPath(dep)+".exploaded.aar/"
        elif self.type == "jar":
            self.projectPath = mvn.dependencyToBasePath(dep)+"/"+dep["version"]
            if not path.exists(self.projectPath):
                os.mkdir(self.projectPath)
            
        if not path.exists(self.path):
            error("No File for "+self.name)
            return False
        for i in mvn.listDependencies(dep):
            name = mvn.getName(i)
            obj = getMvnDependency(name,i)
            self.dependencies.append(obj)
        super().collect()
        
def getMvnDependency(name,dep=None):
    for i in Dependency.globalDeps:
        j = Dependency.globalDeps[i]
        if j.type == "project":
            continue
        if mvn.isMatch(name,j.name):
            obj = j
            break
        elif mvn.isSameArtifact(name,j.name):
            if IGNORE_VERSION_CONFLICT:
                obj = j
                break
            raise Exception(f"Version conflict {j.name} and {name}")
    else:
        if dep == None:
            dep = mvn.parseDependency(name)
        obj = MvnDependency(mvn.getName(dep),dep)
    return obj

def getDependency(name,gradle):
    path = ProjectDependency.resolvePath(gradle.path,name)
    if Dependency.globalDeps.get(path):
        return Dependency.globalDeps.get(path)
    else:
        return ProjectDependency(name,path)


mvn_dep = re.compile("[\"\']([^@\s]*)(@.*)*[\"\']\s*")
jar_dep = re.compile("fileTree\s*\(\s*dir\s*:\s*[\'\"](.*)[\"\']\s*,\s*include\s*:\s*\[\s*((?:[\'\"].*[\"\'],*)(?:,\s*[\'\"].*[\"\'])*\s*),?\s*\]\s*\)")
project_dep = re.compile("project\s*\(\s*[\"\']\:(.*)[\"\']\s*")

def parseDependencyEntry(lib,entry,parents):
    type_ = entry["key"]
    name_ = entry["value"]
    if type_ not in ["implementation","api","compile"]:
        info("Ignoring "+type_+" "+name_)
        return True
    a = re.match(mvn_dep,name_)
    if a:
        lib.addDep(getMvnDependency(a.group(1)))
        return True
    
    a = re.match(jar_dep,name_)
    if a:
        folder = a.group(1)
        files = a.group(2).replace("'","").replace('"',"").split(",")
        if not path.exists(lib.path+"/"+folder):
            return True
        for i in files:
            a  =glob(lib.path+"/"+folder,i)
            lib.addJars(a)
        return True

    a = re.match(project_dep,name_)
    if a:
        lib.addDep(getDependency(a.group(1),lib))
        return True
    else:
        return False
    return False

parserDefs["dependencies"] = {
            '__entry':parseDependencyEntry
            }
if __name__ == "__main__":
    dep = ProjectDependency("Project",FIRST) 
    dep.collect()
    print(dep)
