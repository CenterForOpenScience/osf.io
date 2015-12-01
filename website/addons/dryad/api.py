import urllib, urllib2

from .settings import defaults as dryad_settings

import xml.etree.ElementTree as ET
import xml.dom.minidom


class Dryad(object):
	def __init__(self):
		print "Now in Dryad Object"

	@staticmethod
	def identify():
		response = urllib2.urlopen(dryad_settings.DRYAD_OAI_IDENTIFY)
		html = response.read()
		x = xml.dom.minidom.parseString(html)
		return x
	
	@staticmethod
	def list_set():
		response = urllib2.urlopen(dryad_settings.DRYAD_OAI_LISTSET)
		html = response.read()
		x = xml.dom.minidom.parseString(html)
		return x

	@staticmethod
	def list_metadataformat():
		response = urllib2.urlopen(dryad_settings.DRYAD_OAI_LISTMETADATAFORMAT)
		html = response.read()
		x = xml.dom.minidom.parseString(html)
		return x


	@staticmethod
	def dryad_request(verb="ListIdentifiers", start_date="2010-01-01", prefix="oai_dc", data_set="hdl_10255_3"):
		val = {'verb': verb,
			   'from': start_date,
			   'metadataPrefix' : prefix,
			   'set' : data_set}
		url ="http://www.datadryad.org/oai/request"

		data = urllib.urlencode(val)
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req)
		html = response.read()
		x = xml.dom.minidom.parseString(html)
		return x		

	@staticmethod
	def list_identifiers(start_date="2010-01-01", prefix="oai_dc", data_set="hdl_10255_3"):
		return Dryad.dryad_request("ListIdentifiers", start_date, prefix, data_set)

	@staticmethod
	def list_records(start_date="2010-01-01", prefix="oai_dc", data_set="hdl_10255_3"):
		return Dryad.dryad_request("ListRecords", start_date, prefix, data_set)

	@staticmethod
	def get_record(identifier="oai:datadryad.org:10255/dryad.12", metadataPrefix="oai_dc"):
		val = {'verb': "GetRecord",
			   'identifier': start_date,
			   'metadataPrefix' : prefix}
		url ="http://www.datadryad.org/oai/request"

		data = urllib.urlencode(val)
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req)
		html = response.read()
		x = xml.dom.minidom.parseString(html)
		return x

	@staticmethod
	def get_resumption(token="2010-01-01T00:00:00Z/9999-12-31T23:59:59Z/hdl_10255_3/oai_dc/100"):
		val = {'resumptionToken': token}
		url ="http://www.datadryad.org/oai/request"

		data = urllib.urlencode(val)
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req)
		html = response.read()
		x = xml.dom.minidom.parseString(html)
		return x

class Dryad_DataOne:

	def __init__(self):
		pass

	@staticmethod
	def list(start_n=0, count=20):
		val = {'start': str(start_n ),
			   'count': str(count),
			   'formatId':u'http://www.openarchives.org/ore/terms' }
		url ="http://api.datadryad.org/mn/object"

		data = urllib.urlencode(val)
		req = urllib2.Request(url+'?'+data)
		response = urllib2.urlopen(req)
		html = response.read()
		x = xml.dom.minidom.parseString(html)
		return x

	@staticmethod			
	def metadata(doi="doi:10.5061/dryad.1850/1"):
		url ="http://www.datadryad.org/mn/object"

		req = urllib2.Request(url+"/"+doi)
		response = urllib2.urlopen(req)
		html = response.read()
		x = xml.dom.minidom.parseString(html)
		return x		

	@staticmethod
	def download(doi="doi:10.5061/dryad.1850/1"):
		url ="http://www.datadryad.org/mn/object"

		req = urllib2.Request(url+"/"+doi+'/bitstream')
		response = urllib2.urlopen(req)
		html = response.read()
		"""
		f = open('fileToWriteTo', 'wb')
		bitstreamObject.tofile(f)
		"""
		return html

if __name__ == "__main__":
	dryad = Dryad()
	print dryad.identify().toprettyxml()
	print dryad.list_set().toprettyxml()
	print dryad.list_metadataformat().toprettyxml()
	print dryad.list_identifiers("2010-01-01","oai_dc","hdl_10255_3").toprettyxml()
	print dryad.list_records("2010-01-01","oai_dc","hdl_10255_3").toprettyxml()

	dataone = Dryad_DataOne()
	print dataone.list().toprettyxml()
	print dataone.metadata().toprettyxml()
	print dataone.download()

