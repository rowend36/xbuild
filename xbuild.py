from build_tools import *
from manifest import Manifest
from R_java import updateR
from dependency import ProjectDependency,Dependency
import re
import zipfile

class BuildModes:
    CLEAN = 0
    CLEAN_KEEP_JARDEX = 1
    UNCHANGED = 2
    FAST = 3

def setupPaths(lib):
    p =os.path
    path=lib.path
    lib.java_path = f"{path}/src/main/java"
    lib.manifest = f"{path}/src/main/AndroidManifest.xml"
    lib.res_path = f"{path}/src/main/res"
    lib.build_path = f"{path}/xbuild"
    lib.dex_path = lib.build_path+"/bin/classes.dex"
    lib.aidl_path = f"{path}/src/main/aidl"
    if not os.path.exists(lib.aidl_path):
        lib.aidl_path = None
    if USE_AAPT2:
        flat_path = lib.build_path+"/resources/"
        lib.flat_res_path = flat_path
        lib.flat_res_tree = readFlatResTree(lib,wrap(lib.flat_res_path))    
        if lib.res_path:
            if not p.exists(flat_path):
                os.makedirs(flat_path)
    else:
        lib.res_tree = readResTree(lib,wrap(lib.res_path))

def setupAarPaths(lib):
    zipper = zipfile.ZipFile(lib.path)
    lib.java_path = None
    lib.build_path = f"{lib.projectPath}/xbuild"
    lib.manifest = lib.projectPath+"/AndroidManifest.xml"
    lib.dex_path=None 
    lib.res_path = lib.projectPath+"/res"
    zipper.extractall(lib.projectPath)
    zipper.close()
    if not path.exists(lib.res_path):
        lib.res_path=None
    lib.jar_files = glob(lib.projectPath,"*.jar")
    lib.aidl_path = lib.projectPath+"/aidl"
    if not path.exists(lib.aidl_path):
        lib.aidl_path = None
    libPath = lib.projectPath+"/libs"
    if path.exists(libPath):
        lib.jar_files.extend(glob(libPath,"*.jar"))
    if USE_AAPT2:
        flat_path = lib.build_path+"/resources/"
        lib.flat_res_path = flat_path
        lib.flat_res_tree = readFlatResTree(lib,wrap(lib.flat_res_path))    
        if lib.res_path:
            if not path.exists(flat_path):
                os.makedirs(flat_path)
    else:
        lib.res_tree = readResTree(lib,wrap(lib.res_path))
 
def setupJarPaths(lib):
    lib.manifest = None
    lib.res_path = None
    lib.jar_files = [lib.path]
    lib.build_path = f"{lib.projectPath}/xbuild"
    lib.res_tree=[]
    lib.java_path = None
    lib.dex_path=None
    lib.aidl_path=None

def readResTree(lib,tree):
    for i in lib.dependencies:
        if i.type == "unresolved":
            continue
        #if i.res_path:
        #    if i.res_path in tree:
        #        tree.remove(i.res_path)
        #    tree.append(i.res_path)
        for j in i.res_tree:
            if j in tree:
                tree.remove(j)
            tree.append(j)
            
        #readResTree(i,tree)
    assert(checkSet(tree))
    return tree

def readFlatResTree(lib,tree):
    for i in lib.dependencies:
        if i.type == "unresolved":
            continue
        if not i.res_path:
            continue
        #if i.res_path:
        #    if i.res_path in tree:
        #        tree.remove(i.res_path)
        #    tree.append(i.res_path)
        for j in i.flat_res_tree:
            if j in tree:
                tree.remove(j)
            tree.append(j)
            
        #readResTree(i,tree)
    assert(checkSet(tree))
    return tree

def readDepTree(lib,tree):
    for i in lib.dependencies:
        if i.type == "unresolved":
            continue
        #    if i.res_path in tree:
        #        tree.remove(i.res_path)
        #    tree.append(i.res_path)
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
    assert lib.res_path
    a = None
    if not USE_AAPT2:
        res_path = lib.res_tree
        if not path.exists(gen_path):
            os.makedirs(gen_path)
        a = aapt_package(manifest,res_path,gen_path,lib.type=="project",lib.getOptions())
    else:
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
    print("\n-".join(map(lambda a:a.name,libraries)))
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
        if j.dex_path:
            dexList.append(j.dex_path)
        if path.exists(j.build_path+"/dexLibs"):
            dexList.extend(glob(j.build_path+"/dexLibs","*.dex.jar"))
        assert checkSet(dexList), j.name
    
    mergedPath = app.build_path+"/bin/merged/"
    if not path.exists(mergedPath):
        os.makedirs(mergedPath)
    binPath = app.build_path+"/bin"
    info("merging dex")
    if mode is BuildModes.FAST and path.exists(mergedPath+"/classes.dex"):
        dx_dex(app.getObjs(False),app.dex_path)
        dx_merge(mergedPath+"/classes.dex",app.dex_path,mergedPath+"/classes.dex")
    else:
        dx_dex(app.getObjs(True),app.dex_path)
        dx_merge(mergedPath+"/classes.dex",*dexList)
    apk_unaligned = binPath+f"/{app_name}-unalingned.apk"
    if path.exists(apk_unaligned):
        os.remove(apk_unaligned)
    apk_file = binPath+f"/{app_name}.apk"
    os.system(f"zipmerge {apk_unaligned} "+" ".join(filter(lambda a:a.endswith("jar"),dexList)))
    packager = (USE_AAPT2 and aapt2_package_res) or package_res
    a = packager(app.manifest,app.res_tree,mergedPath,apk_unaligned,app.getOptions())
    if not a:
        return "packaging failed"
    a = sign_align(apk_unaligned,SIGNING_KEY_PATH,apk_file)
    os.remove(apk_unaligned)
    if not a:
        return "signing/zipaligning failed"
    install(apk_file);
    return "Succeeded"

def main(path="."):
    app = ProjectDependency("main",path)
    buildApp(app,"app",BuildModes.FAST)
def mainLibrary(path="."):
    pass
if __name__ == "__main__":
    main(FIRST)

