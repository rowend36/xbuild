from build_tools import *
from manifest import Manifest
from R_java import updateR
from dependency import ProjectDependency,Dependency
import re
import zipfile
class BuildPaths:
    def __init__(self,conf=None):
        super().__init__()
        if not conf:
            conf = {}
        self.java = '/'+conf.get("java_path","src/main/java")
        self.aidl = '/'+conf.get("aidl_path","src/main/aidl")
        self.libs = '/'+conf.get("libs_path","libs")
        self.res = '/'+conf.get("res_path","src/main/res")
        self.manifest = '/'+conf.get("manifest","src/main/AndroidManifest.xml")
        self.build = '/'+conf.get("build_path","xbuild")
        self.key = '/'+conf.get("key_path","main.key")
class BuildModes:
    CLEAN = 0
    CLEAN_KEEP_JARDEX = 1
    UNCHANGED = 2
    FAST = 3

def setupPaths(lib):
    p =os.path
    path=lib.path
    lib.java_path = path + PATHS.java
    lib.manifest = path + PATHS.manifest
    lib.res_path = path + PATHS.res
    lib.build_path = path + PATHS.build
    lib.aidl_path = path + PATHS.aidl
    lib.dex_path = lib.build_path+"/bin/classes.dex"
    if not os.path.exists(lib.aidl_path):
        lib.aidl_path = None
    if USE_AAPT2:
        flat_path = lib.build_path+"/resources/"
        lib.flat_res_path = flat_path
        lib.flat_res_tree = readFlatResTree(lib,wrap(lib.flat_res_path))    
    else:
        lib.res_tree = readResTree(lib,wrap(lib.res_path))

def setupAarPaths(lib):
    zipper = zipfile.ZipFile(lib.path)
    lib.java_path = None
    lib.build_path = lib.projectPath + PATHS.build
    lib.manifest = lib.projectPath+PATHS.manifest
    lib.dex_path=None 
    lib.res_path = lib.projectPath+PATHS.res;
    lib.aidl_path = lib.projectPath+PATHS.aidl;
    libPath = lib.projectPath+PATHS.libs;
    zipper.extractall(lib.projectPath)
    zipper.close()
    if not path.exists(lib.res_path):
        lib.res_path=None
    lib.jar_files = glob(lib.projectPath,"*.jar")
    if not path.exists(lib.aidl_path):
        lib.aidl_path = None
    if path.exists(libPath):
        lib.jar_files.extend(glob(libPath,"*.jar"))
    if USE_AAPT2:
        flat_path = lib.build_path+"/resources/"
        lib.flat_res_path = flat_path
        lib.flat_res_tree = readFlatResTree(lib,wrap(lib.flat_res_path))
    else:
        lib.res_tree = readResTree(lib,wrap(lib.res_path))
 
def setupJarPaths(lib):
    lib.manifest = None
    lib.res_path = None
    lib.jar_files = [lib.path]
    lib.build_path = lib.projectPath + PATHS.build
    lib.res_tree=[]
    lib.java_path = None
    lib.dex_path=None
    lib.aidl_path=None

def readResTree(lib,tree):
    for i in lib.dependencies:
        if i.type == "unresolved":
            continue
        for j in i.res_tree:
            if j in tree:
                tree.remove(j)
            tree.append(j)
    assert(checkSet(tree))
    return tree

def readFlatResTree(lib,tree):
    for i in lib.dependencies:
        if i.type == "unresolved":
            continue
        if not i.res_path:
            continue
        for j in i.flat_res_tree:
            if j in tree:
                tree.remove(j)
            tree.append(j)
    assert(checkSet(tree))
    return tree

def readDepTree(lib,tree):
    for i in lib.dependencies:
        if i.type == "unresolved":
            continue
        if i in tree:
            tree.remove(i)
        tree.append(i)
        readDepTree(i,tree)
    assert(checkSet(tree))
    return tree

def readAidlTree(lib,lists):
    if lib.aidl_path:
        if lib.aidl_path in lists:
            return lists
        lists.append(lib.aidl_path)
        for i in lib.dependencies:
            readAidlTree(i,lists)
    return lists
    
def buildResources(lib,updateChildren=False):
    info("aapt compiling "+lib.name)
    manifest = lib.manifest
    gen_path = lib.build_path+"/gen"
    if not path.exists(gen_path):
        os.makedirs(gen_path)
    
    assert lib.res_path
    a = None
    if not USE_AAPT2:
        res_path = lib.res_tree
        a = aapt_package(manifest,res_path,gen_path,lib.type=="project",lib.getOptions())
    else:
        if not path.exists(lib.flat_res_path):
            os.makedirs(lib.flat_res_path)
        #TODO UNCHANGED
        a = aapt2_compile(lib.res_path,lib.flat_res_path)
        if a:
            a = aapt2_link(lib.flat_res_tree,gen_path,manifest,lib.getOptions())
        else:
            raise Exception("aapt compile failed")
    if not a:
        print(list(map(lambda a: a.name,lib.dependencies)))
        raise Exception("aapt failed")
    if updateChildren:
        R_path = lib.getChildRPaths()
        assert checkSet(R_path), R_path
        updateR(lib.getRPath(),*R_path,update=True)

def build(lib,mode=BuildModes.CLEAN_KEEP_JARDEX):
    info("ecj compiling "+lib.name)
    build_path=lib.build_path
    obj_path = build_path+"/obj"
    bin_path = build_path+"/bin"
    gen_path = build_path+"/gen"
    
    if mode<BuildModes.UNCHANGED:
        if path.exists(obj_path):
            recursiveDelete(obj_path)
        if path.exists(bin_path):
            recursiveDelete(bin_path)
    java_files = []
    java_path = wrap(lib.java_path)
    for i in java_path:
        if path.exists(i):
            java_files.extend(glob(i,"**.java"))
        else:
            pass
    aidl_files = []
    aidl_path = wrap(lib.aidl_path)
    for i in aidl_path:
        if path.exists(i):
            aidl_files.extend(glob(i,"**.aidl"))
        else:
            pass
    source_path = [*java_path,gen_path]
    dexPath = lib.build_path+"/dexLibs/"
    classpath = wrap(f"{PREFIX}/share/java/android.jar")
    if not path.exists(gen_path):
        os.makedirs(gen_path)
    if not path.exists(obj_path):
        os.mkdir(obj_path)
    if not path.exists(bin_path):
        os.mkdir(bin_path)
    #Compile jars    
    if len(lib.getLibs())>0:
        if not path.exists(dexPath):
            os.makedirs(dexPath)
        for i in lib.getLibs():
            filename = path.basename(i)
            path_ = path.join(dexPath + re.sub("\.jar$","",filename)+".dex.jar")
            if mode == BuildModes.CLEAN or not path.exists(path_):
                info("dexing "+filename)
                if not dx_dex(i,path_):
                    if path.exists(path_):
                        os.remove(path_)
                    raise Exception('Failed Dexing '+filename+' for '+lib.name)
    a = lib.getLibs(True)
    b = lib.getObjs(True)
    assert checkSet(a)
    assert checkSet(b)
    classpath.extend(a)
    classpath.extend(b)
    if len(aidl_files) > 0:
        info("running aidl ")
        imports = readAidlTree(lib,[])
        if not aidl_compile(aidl_files,imports,gen_path):
            raise Exception("aidl_failed")
    java_files.extend(glob(gen_path,"**.java"))
    if len(java_files) > 0:
        #TODO UNCHANGED
        a = ecj_compile(java_files,classpath,source_path,obj_path)
        if not a:
            raise Exception("ecj failed")
        return True
    else:
        return False

def buildDependencyTree(head,mode = BuildModes.CLEAN_KEEP_JARDEX):
    if head:
        head.collect()
    libraries = readDepTree(head,wrap(head))[-1::-1]
    debug("\n-".join(map(lambda a:a.name,libraries)))
    
    #Setup paths and build resources
    for dep_lib in libraries:
        if dep_lib.type == "project":
            setupPaths(dep_lib)
        elif dep_lib.type == "aar":
            setupAarPaths(dep_lib)
        elif dep_lib.type == "jar":
            setupJarPaths(dep_lib)
        else:
            warn("Unresolved Dependency "+dep_lib.name)
            continue
        if dep_lib.res_path:
            #most java projects will not compile a
            #switch with non constant values
            #so a way to enforce ids for projects is still of use
            if mode is BuildModes.FAST:
                if dep_lib is head:
                    buildResources(head,False)
            else:
                buildResources(dep_lib,dep_lib is head)
    if mode == BuildModes.FAST:
        build(head)
        return
    for dep_lib in libraries:
        project = None
        if dep_lib.type == "project":
            project = build(dep_lib,mode)
        elif dep_lib.type == "aar":
            project = build(dep_lib,mode)
        elif dep_lib.type == "jar":
            project = build(dep_lib,mode)

def buildApp(app,app_name,mode=BuildModes.CLEAN_KEEP_JARDEX):
    buildDependencyTree(app,mode)
    dexList = []
    for i in Dependency.globalDeps:
        j = Dependency.globalDeps[i]
        #if path.exists(j.dex_path):
            #dexList.append(j.dex_path)
        if path.exists(j.build_path+"/dexLibs"):
            dexList.extend(glob(j.build_path+"/dexLibs","*.dex.jar"))
        assert checkSet(dexList), j.name
    
    mergedPath = app.build_path+"/bin/merged/"
    if not path.exists(mergedPath):
        os.makedirs(mergedPath)
    binPath = app.build_path+"/bin"
    info("merging dex")
    status = False
    if mode is BuildModes.FAST and path.exists(mergedPath+"/classes.dex"):
        status = dx_dex(app.getObjs(False),app.dex_path)
        if status:
            status = dx_merge(mergedPath+"/classes.dex",app.dex_path,mergedPath+"/classes.dex")
        else: return error('Dexing Failed')
    else:
        status = dx_dex(app.getObjs(True),app.dex_path)
        if status:
            status = dx_merge(mergedPath+"/classes.dex",app.dex_path,*dexList)
        else: return error('Dexing Failed')
    if not status:
        return error("Merge Failed")
    apk_unaligned = binPath+f"/{app_name}-unalingned.apk"
    if path.exists(apk_unaligned):
        os.remove(apk_unaligned)
    apk_file = binPath+f"/{app_name}.apk"
    if len(dexList)>0:
        os.system(f"zipmerge {apk_unaligned} "+" ".join(filter(lambda a:a.endswith("jar"),dexList)))
    if USE_AAPT2:
        a = aapt2_package_res(app.manifest,app.flat_res_tree,mergedPath,apk_unaligned,app.getOptions())
    else:
        package_res(app.manifest,app.res_tree,mergedPath,apk_unaligned,app.getOptions())
    if not a:
        return "packaging failed"
    a = sign_align(apk_unaligned,app.path+PATHS.key,apk_file)
    os.remove(apk_unaligned)
    if not a:
        return "signing/zipaligning failed"
    install(apk_file);
    return "Succeeded"

def main(path=".",mode=BuildModes.CLEAN):
    app = ProjectDependency("main",path)
    buildApp(app,"app",mode)
def mainLibrary(path="."):
    pass
if __name__ == "__main__":
    if HELP:
        print('\n    '.join((
            'xbuild.py [-h][-d][-q][-a][-c configfile] [-m CLEAN|FAST|UNCHANGED|SOURCE] [dir]',
                'Xbuild - Utility to build Gradle android projects',
                'h help',
                'd debug',
                'q quiet',
                'c configFile',
                'm BuildMode',
                'l List Dependencies'
                'a Use aapt2 instead of aapt',
                'SOURCE rebuild all source files',
                'CLEAN rebuild both source files and libraries',
                'FAST rebuild main project source files',
                'UNCHANGED unimplemented, works as fast'
                )))
    elif LIST_DEPS:
        dep = ProjectDependency("main",TARGET)
        dep.collect()
        print(dep)
    else:
        PATHS=BuildPaths(CONFIG)
        mode = BuildModes.CLEAN;
        if MODE:
            if MODE == 'FAST':
                mode = BuildModes.FAST
            elif MODE == 'UNCHANGED':
                mode = BuildModes.UNCHANGED
            elif MODE == 'SOURCE':
                mode = BuildModes.CLEAN_KEEP_JARDEX
        main(TARGET,mode)

