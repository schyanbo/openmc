#!/usr/bin/env python

import os
import sys
from xml.dom.minidom import getDOMImplementation

class Xsdir(object):

    def __init__(self, filename):
        self.f = open(filename, 'r')
        self.filename = os.path.abspath(filename)
        self.directory = os.path.dirname(filename)
        self.awr = {}
        self.tables = []

        # Read first section (DATAPATH)
        line = self.f.readline()
        words = line.split()
        if words:
            if words[0].lower().startswith('datapath'):
                index = line.index('=')
                self.datapath = line[index+1:].strip()

        # Read second section
        line = self.f.readline()
        words = line.split()
        assert len(words) == 3
        assert words[0].lower() == 'atomic'
        assert words[1].lower() == 'weight'
        assert words[2].lower() == 'ratios'

        while True:
            line = self.f.readline()
            words = line.split()

            # Check for end of second section
            if len(words) % 2 != 0 or words[0] == 'directory':
                break
            
            for zaid, awr in zip(words[::2], words[1::2]):
                self.awr[zaid] = awr

        # Read third section
        while words[0] != 'directory':
            words = self.f.readline().split()
            
        while True:
            words = self.f.readline().split()
            if not words:
                break

            # Handle continuation lines
            while words[-1] == '+':
                extraWords = self.f.readline().split()
                words = words + extraWords
            assert len(words) >= 7

            # Create XsdirTable object and add to line
            table = XsdirTable(self.directory)
            self.tables.append(table)
            
            # All tables have at least 7 attributes
            table.name = words[0]
            table.awr = float(words[1])
            table.filename = words[2]
            table.access = words[3]
            table.filetype = int(words[4])
            table.address = int(words[5])
            table.tablelength = int(words[6])

            if len(words) > 7:
                table.recordlength = int(words[7])
            if len(words) > 8:
                table.entries = int(words[8])
            if len(words) > 9:
                table.temperature = float(words[9])
            if len(words) > 10:
                table.ptable = (words[10] == 'ptable')

    def to_xml(self):
        # Create XML document
        impl = getDOMImplementation()
        doc = impl.createDocument(None, "cross_sections", None)

        # Get root element
        root = doc.documentElement

        # Add a directory node
        if self.directory:
            directoryNode = doc.createElement("directory")
            text = doc.createTextNode(self.directory)
            directoryNode.appendChild(text)
            root.appendChild(directoryNode)

            for table in self.tables:
                table.path = os.path.basename(table.path)

        # Add a node for each table
        for table in self.tables:
            if table.name[-1] in ['e', 'p', 'u', 'h', 'g' ,'m', 'd']:
                continue
            node = table.to_xml_node(doc)
            root.appendChild(node)

        return doc


class XsdirTable(object):

    def __init__(self, directory=None):
        self.directory = None
        self.name = None
        self.awr = None
        self.filename = None
        self.access = None
        self.filetype = None
        self.address = None
        self.tablelength = None
        self.recordlength = None
        self.entries = None
        self.temperature = None
        self.ptable = False

    @property
    def path(self):
        if self.directory:
            return os.path.join(self.directory, self.filename)
        else:
            return self.filename

    @path.setter
    def path(self, value):
        self.diretory = ''
        self.filename = value

    @property
    def metastable(self):
        # Only valid for neutron cross-sections
        if not self.name.endswith('c'):
            return

        # Handle special case of Am-242 and Am-242m
        if self.zaid == '95242':
            return 1
        elif self.zaid == '95642':
            return 0

        # All other cases
        A = int(self.zaid) % 1000
        if A > 600:
            return 1
        else:
            return 0

    @property
    def zaid(self):
        return self.name[:self.name.find('.')]

    def to_xml_node(self, doc):
        node = doc.createElement("ace_table")
        node.setAttribute("name", self.name)
        for attribute in ["alias", "zaid", "type", "metastable",
                          "awr", "temperature", "binary", "path"]:
            if hasattr(self, attribute):
                # Join string for alias attribute
                if attribute == "alias":
                    if not self.alias:
                        continue
                    string = " ".join(self.alias)
                else:
                    string = "{0}".format(getattr(self,attribute))

                # Skip metastable and binary if 0
                if attribute == "metastable" and self.metastable == 0:
                    continue
                if attribute == "binary" and self.binary == 0:
                    continue

                # Create attribute node
                # nodeAttr = doc.createElement(attribute)
                # text = doc.createTextNode(string)
                # nodeAttr.appendChild(text)
                # node.appendChild(nodeAttr)
                node.setAttribute(attribute, string)
        return node


if __name__ == '__main__':
    # Read command line arguments
    if len(sys.argv) < 3:
        sys.exit("Usage: convert_xsdir.py  xsdirFile  xmlFile")
    xsdirFile = sys.argv[1]
    xmlFile = sys.argv[2]

    # Read xsdata and create XML document object
    xsdirObject = Xsdir(xsdirFile)
    doc = xsdirObject.to_xml()
    
    # Reduce number of lines
    lines = doc.toprettyxml(indent='  ')

    # Write document in pretty XML to specified file
    f = open(xmlFile, 'w')
    f.write(lines)
    f.close()