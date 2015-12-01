# This should be the browser for dryad

from website.addons.dryad import api

import httplib
import logging
import datetime

from flask import request
from framework.flask import redirect
from framework.exceptions import HTTPError

from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon, must_be_valid_project, must_be_addon_authorizer
from website.project.views.node import _view_project

from website.util import api_url_for
from website.util import rubeus

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon

logger = logging.getLogger(__name__)

import xml.etree.ElementTree as ET

from urllib2 import HTTPError

@must_be_valid_project
@must_have_addon('dryad', 'node')
def check_dryad_doi(node_addon, **kwargs):
    doi = request.args["doi"]
    pid =  kwargs['pid']
    auth=kwargs['auth']
    try:
        d = Dryad_DataOne()
        m = d.metadata(doi)
    except HTTPError as e:
        return {'result': False}
    return {'result' : True}


@must_be_valid_project
@must_have_addon('dryad', 'node')
def set_dryad_doi(node_addon, **kwargs):
    doi = request.args["doi"]
    pid =  kwargs['pid']
    auth=kwargs['auth']
    d = Dryad_DataOne()
    try:
        m = d.metadata(doi)
    except HTTPError as e:
        return redirect("/project/{}".format(pid))
        
    node_addon.set_doi(doi,m.getElementsByTagName("dcterms:title")[0].firstChild.wholeText, auth)
    
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
def dryad_browser(**kwargs):
    return dryad_page(**kwargs)

@must_be_valid_project
@must_have_addon('dryad', 'node')
def dryad_page(**kwargs):
    node = kwargs['node']
    pid =  kwargs['pid']
    auth=kwargs['auth']


    count=10
    if "count" in request.args:
        count=int(request.args["count"]) 
    start=0
    if "start" in request.args:
        start=int(request.args["start"] )

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
    ret.update(dryad.update_json() )
    ret.update(_view_project(node, auth, primary=True)) 

    return ret



@must_be_valid_project
@must_have_addon('dryad', 'node')
def search_dryad_page(**kwargs):
    node = kwargs['node']
    pid =  kwargs['pid']
    auth=kwargs['auth']


    count=10
    if "count" in request.args:
        count=int(request.args["count"]) 
    start=0
    if "start" in request.args:
        start=int(request.args["start"] )
    query=""
    if "query" in request.args:
        query = request.args["query"]

    dryad = node.get_addon('dryad')
    


    d = Dryad_SOLR()
    x = d.basic_query(query)

    docs = x.getElementsByTagName("doc")


    count = int(x.getElementsByTagName("result")[0].attributes["numFound"].value )
    start = int(x.getElementsByTagName("result")[0].attributes["start"].value)
    total = int(x.getElementsByTagName("result")[0].attributes["numFound"].value)

    ret = {"end": start+count,
            "start": start,
            "total":total,
            "content": "",
            'next_dryad':request.path+"?count={}&start={}".format(count, start+count),
            'previous_dryad':request.path+"?count={}&start={}".format(count, start-count) }

    objectList = ET.Element("ul")
    for doc in docs:
         
        title_elements = [ i.firstChild.firstChild.wholeText for i in  doc.getElementsByTagName("arr") if i.hasAttribute("name") and i.getAttribute("name")=="dc.title_ac"  ]
        title_element=""
        if len(title_elements)>0:
            title_element=title_elements[0]

        objInfo = ET.SubElement(objectList, "li")
        objInfo.text = title_element
        sublist = ET.SubElement(objInfo,"ul")

        author_list = [ i for i in  doc.getElementsByTagName("arr") if i.hasAttribute("name") and i.getAttribute("name")=="dc.contributor.author_ac"  ][0]
        author_list = [ i.firstChild.wholeText for i in  author_list.getElementsByTagName("str")   ]
        authors="Authors: "+", ".join(author_list)

        authorel = ET.SubElement(sublist, "li")
        authorel.text = authors

        #pick out the identifier: dc.identifier
        identifier = [ i.firstChild.firstChild.wholeText for i in  doc.getElementsByTagName("arr") if i.hasAttribute("name") and i.getAttribute("name")=="dc.identifier"]

        identifier=identifier[0]
        id_item = ET.SubElement(sublist,"li")
        id_button = ET.SubElement(id_item, "a")
        id_button.text ="View Package Externally"
        id_button.attrib["href"] = "http://datadryad.org/resource/{}".format(identifier) if not "http" in identifier else identifier

        if "doi" in identifier:
            add_item = ET.SubElement(sublist,"li")
            add_button = ET.SubElement(add_item, "a")
            add_button.text ="Set Node Data to This"
            add_button.attrib["href"] = "/project/{}/dryad/add?doi={}".format(pid, identifier)

    ret.update({"content": ET.tostring(objectList)})
    ret.update(dryad.config.to_json() )
    ret.update(dryad.update_json() )
    ret.update(_view_project(node, auth, primary=True)) 

    return ret

def dryad_addon_folder(node_settings, auth, **kwargs):    
    # Quit if no dataset linked
    if node_settings.dryad_package_doi == None:
        return []

    node = node_settings.owner
    urls = {
        'download': 'http://api.datadryad.org/mn/object/'+node_settings.dryad_package_doi.replace('/http://dx.doi.org/', 'doi:')+'/bitstream',
        'view': 'http://api.datadryad.org/mn/object/'+node_settings.dryad_package_doi.replace('/http://dx.doi.org/', 'doi:')
    }
    

    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name=node_settings.folder_name,
        doi=node_settings.dryad_package_doi,
        permissions=auth,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
        urls=urls
    )

    return [root]
    


@must_be_contributor_or_public
@must_have_addon('dryad', 'node')
def dryad_root_folder_public(node_addon, auth, **kwargs):
    return dryad_hgrid_root(node_addon, auth=auth)
