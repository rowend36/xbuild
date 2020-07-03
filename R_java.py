from build_utils import *
import re
from parser import *

def updateR(master_R,*sub_R,update=False):
    text = stropen(master_R).split("\n")
    master = R_toDict(text)
    for a in sub_R:
        text = stropen(a).split("\n")
        sub = R_toDict(text)
        mismatch = False
        for i in sub["tree"]:
            for j in sub["tree"][i]:
                assert i in master["tree"], 'No class '+i
                assert j in master["tree"][i], 'No property '+i
                if sub["tree"][i][j]["value"] != master["tree"][i][j]["value"]:
                    debug("Mismatch %s.%s in %s"%(i,j,a))
                    if update:
                        mismatch = True
                        sub["tree"][i][j]["value"] = master["tree"][i][j]["value"]
        if mismatch:
            R_toString(sub,a)

def R_toDict(text):
    pos = Pos()
    pos.ch = 0
    pos.line = 0
    resource = None
    root={}
    root["package"] = readPackage(text,pos)["package"]
    root["class"] = readClass(text,pos)["class"]
    master = root["tree"] = {}
    class_ = eatClass(text,pos)
    while class_:
        master[class_['class']]={}
        constant_ = eatArrayConstant(text,pos)
        while constant_:
            master[class_['class']][constant_["name"]]=constant_
            eatDecorator(text,pos)
            constant_ = eatArrayConstant(text,pos)
        readCloseCurly(text,pos)
        eatDecorator(text,pos)
        class_ = eatClass(text,pos)
    readCloseCurly(text,pos)
    return root

def R_toString(dictionary,filename,indent="    ",newline="\r\n"):
    text = "/* Updated By XBuild R Updater */"
    text += newline
    text += "package {package};".format(package=dictionary["package"])
    text += newline
    text += "public final class {name}".format(name=dictionary["class"])
    text += "{"+newline
    for i in dictionary["tree"]:
        pop = dictionary["tree"][i]
        text+=indent
        text+="public static final class {name}".format(name = i)
        text+="{"+newline
        for j in pop:
            final = "public static "
            if pop[j]["final"]:
                final += "final "
            text+=indent*2
            if pop[j]['value'][0]=="{":
                text+=final+"int[] {name} = {value};".format(name=j,value=pop[j]["value"])
            else:
                text+=final+"int {name} = {value};".format(name=j,value=pop[j]["value"])
            text+=newline
        text+=newline+indent+"}"+newline
    text+="}"
    a = open(filename,"w")
    a.write(text)
    a.close()


class_re = re.compile("((?:public|private)\s)*\s*((?:static)\s)*\s*((?:final)\s)*\s*class\s+(\w+)")
package_re = re.compile("package ([\w|\.]+);")
constant_re = re.compile("public\s+static\s+(?:(final)\s+)?int\s+(\w+)\s*=\s*(\w+)\s*;")
array_constant_re = re.compile("public\s+static\s+(?:(final)\s+)?int\s*\[\]\s+(\w+)\s*=\s*{\s*")

def eatPackage(str_R,pos):
    eatComment(str_R,pos)
    result = re.match(package_re,str_R[pos.line][pos.ch:])
    if result:
        pos.ch = pos.ch+len(result.group(0))
        eatSpace(str_R,pos)
        return {"package":result.group(1)}
    return False

readPackage = notFalse("Expected package declaration")(eatPackage)

def eatClass(str_R,pos):
    eatComment(str_R,pos)
    result = re.match(class_re,str_R[pos.line][pos.ch:])
    if result:
        pos.ch = pos.ch+len(result.group(0))
        eatSpace(str_R,pos)
        readOpenCurly(str_R,pos)
        return {"class":result.group(4)}
    return False

readClass = notFalse("Expected class declaration")(eatClass)

def eatDecorator(str_R,pos):
    eatToken(str_R,pos,"@.*")

def eatConstant(str_R,pos):
    eatComment(str_R,pos)
    result = re.match(constant_re,str_R[pos.line][pos.ch:])
    if result:
        pos.ch = pos.ch+len(result.group(0))
        eatSpace(str_R,pos)
        return {"name":result.group(2),"final":not not result.group(1),"value":result.group(3)}
    return False
    
@notFalse("Array Constant",True)
def eatArrayConstant(str_R,pos):
    a = eatConstant(str_R,pos)
    if a:
        return a
    a = eatToken(str_R,pos,array_constant_re)
    if a:
        i = pos.line
        text = str_R[pos.line][pos.ch:]
        j = pos.ch
        while True:
            if "}" in text:
                j += text.index("}")
                break
            i+=1
            if i == len(str_R):
               raise Exception("Eof while parsing result")
            text=str_R[i]
            j = 0
        end = Pos()
        end.line=i
        end.ch=j
        value = createToken(str_R,pos,end,"")[1]
        pos.line=i
        pos.ch=j+1
        assert(eatToken(str_R,pos,";"))
        obj = {'name':a.group(2),'array':True,'final':not not a.group(1),'value':"{"+value.replace("\n"," ").replace(","," , ").replace("  "," ").replace("  "," ")+"}"}
        return obj
    return False

@notFalse("Expected open bracket")
def readOpenCurly(str_R,pos):
    return eatToken(str_R,pos,"{")

@notFalse("Expected close bracket")
def readCloseCurly(str_R,pos):
    return eatToken(str_R,pos,"};?")

