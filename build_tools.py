#!/data/data/com.termux/files/usr/bin/bash
import os
from build_utils import *
path = os.path
mapper = None

if USE_AAPT2:
    mapper = {
        "minSdkVersion":"min-sdk-version",
        "targetSdkVersion":"target-sdk-version",
        "versionCode":"version-code",
        "versionName":"version-name",
        "product":"product"
            }
else:
    mapper = {
        "minSdkVersion":"min-sdk-version",
        "targetSdkVersion":"target-sdk-version",
        "versionCode":"version-code",
        "versionName":"version-name",
        "product":"product"
            }
def aapt_package(manifest,res_array,java_path,final_ids=False,options={}):
    res_array = wrap(res_array)
    command = "aapt package --error-on-failed-insert "
    if len(res_array)>1:
        command+=" --auto-add-overlay "
        pass
    if not final_ids:
        command+=" --non-constant-id "
    for i in options:
        a = mapper[i]
        command+="--{option} {name} ".format(name=options[i],option=a)
    command += f"-M {manifest} "
    for i in res_array:
        command+=f"-S {i} "
    command+=f"-J {java_path} "
    command+=f"-I {AAPT_ANDROID_JAR} "
    command+="-m "
    return os.system(command) == 0

def aapt2_compile(res_path,output_path,stub=None,legacy=False):
    if stub:
        raise Exception("Expected 2 args got 3")
    res_array = glob(res_path,'**')
    legacy = (legacy and "legacy") or ""
    for i in res_array:
        if system(f"aapt2 compile {i} {legacy} -o {output_path}") != 0:
            return False
    return True
def aapt2_link(res_paths,java_path,manifest,options={},final_ids=False):
    _temp_id=0
    def tempfile(text):
        nonlocal _temp_id
        _temp_id+=1
        filer = f"args{_temp_id}.txt"
        argfile = open(filer,'w')
        argfile.write(text)
        argfile.close()
        return filer

    command = "aapt2 link "
    res_paths = res_paths[-1::-1]
    res_array = []
    for i in res_paths:
        res_array.append("@"+tempfile(" ".join(glob(i,"*flat"))))
    command += " --auto-add-overlay "
    if not final_ids:
        command+=" --non-final-ids "
    for i in options:
        a = mapper[i]
        command+="--{option} {name} ".format(name=options[i],option=a)
    command += f"--manifest {manifest} "
    command+=f"--java {java_path} "
    command+=f"-I {AAPT_ANDROID_JAR}" 
    command+=f" -o linked.zip "
    command+="-R "+" -R ".join(res_array)
    return os.system(command) == 0


def ecj_compile(java_files,classpath,sourcepath,output_path):
    java_files=wrap(java_files)
    classpath=wrap(classpath)
    sourcepath=wrap(sourcepath)
    command="ecj "
    command+=f"-d {output_path} "
    if classpath:
        command+="-classpath "
        command+=":".join(classpath)
    if sourcepath:
        command+=" -sourcepath "
        command+=":".join(sourcepath)
    command+=" "+f" ".join(java_files)
    return os.system(command) == 0

def aidl_compile(aidl_files,imports_path,output_path):
    preprocess = AIDL_FRAMEWORK
    inputs = " ".join(aidl_files)
    imports  = ""
    for i in imports_path:
        imports += f"-I{i} "
    return os.system(f"aidl -p{preprocess} {imports}{inputs} -o{output_path}") == 0
def dx_dex(obj_path,output_path):
    command = "dx --dex "
    if output_path:
        command+=f"--output {output_path} "
    command+=" ".join(wrap(obj_path))
    return os.system(command) == 0

def dx_merge(output_path,*dexfiles):
    command =f"exec dalvikvm -Xmx256m -cp {DX_JAR_FILE} dx.dx.merge.DexMerger "
    command += output_path+" "
    command += " ".join(dexfiles)
    return os.system(command) == 0
def aapt2_package_res(manifest,res_array,classes_dex_dir,apk_file,options={}):
    command = f"zipmerge {apk_file} linked.zip"
    result = os.system(command)
    if result == 0:
        path_dir = os.getcwd()
        apk_file = path.realpath(apk_file)
        command=f"cd {classes_dex_dir} && zip {apk_file} classes.dex;cd {path_dir}"
        return os.system(command) == 0
    return result == 0
     
def package_res(manifest,res_array,classes_dex_dir,apk_file,options={}):
    res_array = wrap(res_array)
    command = "aapt package -u "
    if len(res_array) >1:
        command+="--auto-add-overlay "
    for i in options:
        a = mapper[i]
        command+="--{option} {name} ".format(name=options[i],option=a)
    command+=f"-M {manifest} "
    command+="-S "+(" -S ").join(res_array)
    command+=f" -F {apk_file}"
    result = os.system(command)
    if result == 0:
        path_dir = os.getcwd()
        apk_file = path.realpath(apk_file)
        command=f"cd {classes_dex_dir} && aapt remove -f {apk_file} classes.dex && aapt add -f {apk_file} classes.dex;cd {path_dir}"
        return os.system(command) == 0
    return result == 0
        
def sign_align(apk_file,key_file,output_path):
    command = f"zipalign -f 4 {apk_file} {apk_file}zipalign"
    result = os.system(command)
    if result == 0:
        command=f"apksigner {key_file} {apk_file}zipalign {output_path}"
        return os.system(command) == 0
    return result == 0

def setupStorage():
    os.system("test ! -d ~/storage && termux-setup-storage")
    os.system(f"test ! -d {BUILD_APK_PATH} && mkdir -p $BUILD_APK_PATH")

def install_tools():
    ## Check required package and install if not installed
    for i in REQ_PKG:
        exists=os.popen("which "+i).read()
        if not exists:
            info(f"Installing {i}")
            os.system("apt install -y "+i)
        else:
            info(f"{i} installed")

def install(apk_file):
    a = os.system(f"chmod 644 {apk_file}")
    setupStorage()
    a = os.system(f"cp {apk_file} {BUILD_APK_PATH}/app.apk")
    ##For some reason termux intents to start installation fail. The source code for the stub app used is in embedded in installer-source.apk
    os.system(f"am start -n com.tmstudios.autoinstaller/com.tmstudios.autoinstaller.MainActivity -d \"file:///sdcard/Download/buildAPKs/app.apk\"")
 
