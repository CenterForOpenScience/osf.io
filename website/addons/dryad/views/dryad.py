# This should be the browser for dryad

from website.addons.dryad import api

import httplib
import logging
import datetime
import browser

from flask import request
from framework.flask import redirect

from framework.exceptions import HTTPError
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon, must_be_valid_project
from website.project.views.node import _view_project

from website.addons.dryad.api import Dryad_DataOne

logger = logging.getLogger(__name__)

import xml.etree.ElementTree as ET

@must_be_valid_project
@must_have_addon('dryad', 'node')
def set_dryad_doi(node_addon, **kwargs):
    doi = request.args["doi"]
    pid =  kwargs['pid']
    #now we gotta 
    d = Dryad_DataOne()
    m = d.metadata(doi)
    node_addon.dryad_title = m.getElementsByTagName("dcterms:title")[0].firstChild.wholeText
    node_addon.dryad_doi = doi
    meta_data = {}
    m_list = [  'dcterms:type',
                'dcterms:creator',
                'dcterms:title',
                'dcterms:identifier',
                'dcterms:subject',
                'dwc:scientificName',
                'dcterms:temporal',
                'dcterms:dateSubmitted',
                'dcterms:available',
                'dcterms:provenance',
                'dcterms:isPartOf']
    for m_item in m_list:
        m_elements = m.getElementsByTagName(m_item)
        temp = []
        for m_el in m_elements:
            temp.append(m_el.firstChild.wholeText)
        meta_data[m_item] = temp
    node_addon.dryad_metadata.append( str(meta_data) )
    node_addon.dryad_doi_list.append(doi)

    node_addon.save()
    #now, redirect back to the original homepage
    return redirect("/project/{}".format(pid))
    
@must_be_valid_project
@must_have_addon('dryad', 'node')
def remove_dryad_doi(node_addon, **kwargs):
    doi = request.args["doi"]
    pid =  kwargs['pid']
    #remove item from list
    node_addon.dryad_doi_list.remove(doi)

    node_addon.save()
    #now, redirect back to the original homepage
    return {}
    



@must_be_valid_project
@must_have_addon('dryad', 'node')
def dryad_page(**kwargs):
    node = kwargs['node']
    pid =  kwargs['pid']
    auth=kwargs['auth']

    count=10
    start=0
    try:
        count = int(request.args["count"])
    except Exception:
        count=10
    try:
        start = int(request.args["start"] )
    except Exception:
        start=0


    dryad = node.get_addon('dryad')
    

    d = Dryad_DataOne()
    logger.info("Getting Package List from Dryad DataOne API")
    x = d.list(count=count, start_n=start)
    logger.debug( x.toprettyxml() )
    count = int(x.getElementsByTagName("d1:objectList")[0].attributes["count"].value )
    start = int(x.getElementsByTagName("d1:objectList")[0].attributes["start"].value)
    total = int(x.getElementsByTagName("d1:objectList")[0].attributes["total"].value)

    ret = {"end": start+count,
            "start": start,
            "total":total,
            "content": "",
            'next_dryad':request.path+"?count={}&start={}".format(count, start+count),
            'previous_dryad':request.path+"?count={}&start={}".format(count, start-count) }
    #Compute out the next and previous buttons


    objectList = ET.Element("ul")

    for obj in x.getElementsByTagName("objectInfo"):
        ident = obj.getElementsByTagName("identifier")[0].firstChild.wholeText
        size = obj.getElementsByTagName("size")[0].firstChild.wholeText
        doi = "doi:"+ident.split("dx.doi.org/")[1].split("?")[0]
        
        objInfo = ET.SubElement(objectList, "li")
        objInfo.text = doi
        logger.info("Getting MetaData for {} from Dryad DataOne API".format(doi) )      
        meta = d.metadata(doi)
        objInfo.text = meta.toprettyxml()
        title = meta.getElementsByTagName("dcterms:title")[0].firstChild.wholeText
        authors = "Authors:"+", ".join([ i.firstChild.wholeText for i in meta.getElementsByTagName("dcterms:creator")])
        objInfo.text = title

        sublist = ET.SubElement(objInfo,"ul")

        authorel = ET.SubElement(sublist, "li")
        authorel.text = authors

        authorel = ET.SubElement(sublist, "li")
        authorel.text = "Identifier:"+ident
        #now create the addon that will add this to the project
        add_item = ET.SubElement(sublist,"li")
        add_button = ET.SubElement(add_item, "a")
        add_button.text ="Set Node Data to This"
        add_button.attrib["href"] = "/project/{}/dryad/add?doi={}".format(pid, doi)



    ret.update({"content": ET.tostring(objectList)})
    ret.update(dryad.config.to_json() )
    ret.update(_view_project(node, auth, primary=True)) 

    return ret
