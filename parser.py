import functools
import re

class Pos:
    def __init__(self):
        super().__init__()
        self.line = 0
        self.ch = 0

def createToken(text,start,end,token):
    pop = ""
    if start.line==end.line:
        pop = text[start.line][start.ch:end.ch]
    else:
        pop += text[start.line][start.ch:]+'\n'
        pop += '\n'.join(text[start.line+1:end.line])
        if end.ch>0:
            pop += '\n'+text[end.line][:end.ch]
    return (token,pop,f"{start.line},{start.ch}-{end.line},{end.ch}")

def notFalse(error,ignore=False):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(str_R,pos,*args,**kwargs):
            start = Pos()
            start.line = pos.line
            start.ch = pos.ch
            a = func(str_R,pos,*args,**kwargs)
            if not a and not ignore:
                raise Exception(error +" > line:{line},ch:{ch}".format(line=pos.line+1,ch=pos.ch))
            return a
        return wrapper
    return decorator

def eatSpace(str_R,pos):
    start = pos.line
    st = pos.ch
    while start<len(str_R):
        while st<len(str_R[start]):
            if str_R[start][st] not in ['\n','\r','\t',' ']:
                break
            st += 1
        else:
            st = 0
            start+=1
            continue
        break
    pos.line=start
    pos.ch=st

def eatToken(str_R,pos,regex):
    eatComment(str_R,pos)
    result = re.match(regex,str_R[pos.line][pos.ch:])
    if result:
        pos.ch = pos.ch+len(result.group(0))
        eatSpace(str_R,pos)
        return result
    return False

@notFalse("Comment",True)
def eatComment(str_R,pos):
    eatSpace(str_R,pos)
    start = str_R[pos.line][pos.ch]
    if start != "/":
        return False
    next = str_R[pos.line][pos.ch+1]
    if next == "/":
        pos.line+=1
        pos.ch=0
        eatComment(str_R,pos)
        eatSpace(str_R,pos)
        return True
    elif next == "*":
        rem = str_R[pos.line][pos.ch:]
        if "*/" in rem:
            end = rem.index("*/")
            pos.ch = end+2
            eatComment(str_R,pos)
            eatSpace(str_R,pos)
            return True
        i = pos.line+1
        while i<len(str_R):
            if "*/" in str_R[i]:
                end = str_R[i].index("*/")
                pos.line=i
                pos.ch=end+2
                eatComment(str_R,pos)
                eatSpace(str_R,pos)
                return True
            i+=1
        raise "Unexpected eof when reading comment"
    else:
        return False
