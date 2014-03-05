from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import subprocess
import os

# We'll use json.loads for parsing the JSON data.
import json

import citeproc

from citeproc.py2compat import *

#Import the citeproc-py classes we'll use below.
from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

__author__ = 'azeem'

CSL_PATH = 'styles'


def to_citation(project_data, citation_style, formatter_Style):
    """Format an OSF project as a citation.

    :param project_data: JSON-style dictionary of project information
    :param citation_style: File name of citation xml document, including directory name (hence OS.path.join when you call the function)
    :param formatter: Citeproc formatter (e.g. formatter.plain, formatter.html)
    """

    bibliography = CitationStylesBibliography(CitationStylesStyle(os.path.join(CSL_PATH, citation_style)),
                                              CiteProcJSON([project_data]),
                                              formatter_Style)

    citation1 = Citation([CitationItem(project_data['id'])])
    bibliography.register(citation1)
    return bibliography.bibliography()


def to_machine_readable(utilname, csl_input):
    """following conversion from JSON to CSLformat (bibtex in this case), this method converts that to XMLintermediary
    and then to final user specified format"""

    texText = to_citation(csl_input, 'bibtex.csl', formatter.plain)

    bibtexTerminal = subprocess.Popen(["echo", texText], stdout = subprocess.PIPE)
    xmlTerminal = subprocess.Popen(["bib2xml"], stdin = bibtexTerminal.stdout, stdout = subprocess.PIPE)
    finalForm = subprocess.check_output([utilname], stdin = xmlTerminal.stdout)
    return finalForm

#print (to_citation(sample,os.path.join(CSL_PATH, 'harvard1.csl'), formatter.plain))

#print(to_machine_readable('xml2bib', sample))