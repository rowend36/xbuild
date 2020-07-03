import re
import sys
from build_utils import *
from build_tools import mapper
from parser import eatToken,notFalse,eatSpace,eatComment,Pos

def parseGradle(lib,flavor=None):
    info("Reading "+lib.gradleFile)
    text = stropen(lib.gradleFile)
    lines = None
    no = 0
    hasDependencies = False
    lines = text.split("\n")
    pos = Pos()
    pos.line=pos.ch=0
    b = []
    while pos.line<len(lines):
        a = eatGroup(lines,pos,'root')
        if a:
            b.extend(a["value"])
    executeGradle(lib,{'type':'group','key':"root","value":b})
    return b

def parseConfiguration(lib,entry,parents):
    if entry["type"] == "entry":
        a = entry["key"]
        if a in mapper:
            lib.options[a] = entry['value'].replace("\"","").replace("'","")
            return True
        info("Unknown configuration "+entry["key"])
        return False
    else:
        return False
    return False

def throwBack(lib,entry,parents):
    return executeGradle(lib,entry,parents[:-1])

parserDefs = {
        "android":{
            "defaultConfig":{
                "__":throwBack,
                },
            "__entry":parseConfiguration,
            "__group":{
                '__group':throwBack,
                },
            "dependencies":throwBack
            },
        "apply":lambda  *a:True
        }

def executeGradle(lib,part,root=[]):
    ##Executes parserDefs
    assert type(part) is dict
    a = {"root":parserDefs}
    for i in root:
        a = a.get(i) or a.get("__group")
        if a is None:
            return False 
    c = part["type"]
    alt1 = a.get("__"+c) 
    alt2 = a.get("__")
    a = a.get(part["key"])
    if not a:
        a = alt1
        alt1 = alt2
        if not a:
            a = alt1
            alt1 = None
            if not a:
                return False
    for alt in (a,alt1,alt2,None):
        a = alt
        if not alt:
           break 
        if type(alt) is not dict:
            if a(lib,part,root): 
                return True
        else:
            break
    if a is None:
        return False
    
    u = None
    if part["type"]=="group":
        u = part["value"]
    else:
        return False
    new_root = [*root,part["key"]]
    for k in u:
        b = k["type"]
        c = None
        if not executeGradle(lib,k,new_root):
            debug('Unknown '+((b and (b+"('"+str(k.get('key'))+"')")) or "text")+' in file:'+".".join(new_root))
        continue
    return True
 
def eatGroup(lines,pos,name):
    values = []
    while pos.line<len(lines):
        eatComment(lines,pos)
        a = eatGroupHeader(lines,pos)
        if a:
            values.append(a)
            continue
        a = eatToken(lines,pos,"(\w+)\s+(.*[^\s}])(})?$")
        if a:
            values.append({"type":"entry","key":a.group(1),"value":a.group(2)})
            if a.group(3):
                break
            continue
        a = eatToken(lines,pos,"((?!}|(//)|(/\*)).)*(})?")
        if a:
            if a.group(1):
                values.append({"type":None,"value":a.group(1)})
            if a.group(4):
                break
    return {"type":"group","key":name,"value":values}

def eatGroupHeader(lines,pos):
    head = eatToken(lines,pos,"(\w+)\s*{")
    if not head:
        return False
    return eatGroup(lines,pos,head.group(1))

