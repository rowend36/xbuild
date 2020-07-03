from build_utils import *
import xml.dom.minidom as parser
from xml.parsers.expat import ExpatError

class Manifest:
    def __init__(self,filename):
        super().__init__()
        self.dom = parser.parse(filename)
    def getPackageName(self):
        return self.dom.getElementsByTagName("manifest").item(0).getAttribute("package")
if __name__ == "__main__":
    print(Manifest("../src/main/AndroidManifest.xml").getPackageName())

