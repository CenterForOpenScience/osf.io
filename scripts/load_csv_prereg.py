""" Load pre-reg questions into schema from csv file
"""

import csv
import urllib2
import logging
import os
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

""" Given a question number, returns tuple containing page id and index of question on page
"""
def getPage(quest_num):
	pageDir = {'page1':['01', '02', '03', '04'], 'page2':['05', '06', '07', '08'], 'page3':['09', '10', '11', '12', '13', '14', '15'], 'page4':['16', '17', '18', '19', '20', '21'], 'page5':['22']}
	for page in pageDir:
		for question in pageDir[page]:
			if (quest_num == question):
				index = pageDir[page].index(question)
				return (page, index)
	return "Question not found."

# use json.dump(<data>, <filename>) to write json to file
def main():
	__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

	preregContent = os.path.join(__location__, 'preregcontent.csv');
	jsonFileDir = os.path.realpath(os.path.join(os.getcwd(), 'website/project/metadata'))
	preregSchema = os.path.join(jsonFileDir, 'prereg-prize-test.json')

	with open(preregSchema) as json_file:
		json_data = json.load(json_file)
		print json_data['pages'][0]['id']

		with open(preregContent, 'rU') as csvfile:
			cr = csv.reader(csvfile)
			cr.next()
			prevQuestionNumber = ""
			currentPage = ""
			for row in cr:
				label = row[0].split('_')
				questionNumber = label[0]
				questionPart = label[1]
				if (questionNumber != prevQuestionNumber):
					currentPage = getPage(questionNumber)
				
				#print currentPage
				# getting list out of range index 
				#print json_data['pages']['id' == currentPage[0]]['questions'][int(currentPage[1])]

if __name__ == '__main__':
    main()
    #print getPage('03')
