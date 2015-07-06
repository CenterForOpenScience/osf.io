""" Load pre-reg questions into schema from csv file
"""

import csv
import urllib2
import logging
import os
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

""" Given a question number, returns list containing page id, page index, and index of question on page
"""
def getPage(quest_num):
	pageDir = {'page1':['01', '02', '03', '04'], 'page2':['05', '06', '07', '08'], 'page3':['09', '10', '11', '12', '13', '14', '15'], 'page4':['16', '17', '18', '19', '20', '21'], 'page5':['22']}
	for page in pageDir:
		for question in pageDir[page]:
			if (quest_num == question):
				questionIndex = pageDir[page].index(question)
				pageIndex = getPageIndex(page)
				return [page, pageIndex, questionIndex]
	return "Question not found."

def getPageIndex(pageName):
	pageDir = {'page1': 0, 'page2': 1, 'page3': 2, 'page4': 3, 'page5': 4}
	for page in pageDir:
		if page == pageName:
			return pageDir[page]
	return "Page not found."

def getLabel(rowType):
	typeDir = {'QUESTION': 'title', 'EXPLAIN': 'description', 'HELP': 'help'}

	for typeOption in typeDir:
		if (typeOption == rowType):
			return typeDir[typeOption]
		elif (rowType.startswith('MC')):
			mc = rowType.split('C')
			index = int(mc[1]) - 1;
			return (mc[1], index)

# use json.dump(<data>, <filename>) to write json to file
def main():
	__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

	preregContent = os.path.join(__location__, 'preregcontent.csv');
	jsonFileDir = os.path.realpath(os.path.join(os.getcwd(), 'website/project/metadata'))
	preregSchema = os.path.join(jsonFileDir, 'prereg-prize-test.json')

	with open(preregSchema) as json_file:
		json_data = json.load(json_file)
		multipleChoice = {}

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
					prevQuestionNumber = questionNumber
					currentPage = getPage(questionNumber)

				rowType = getLabel(questionPart)

				if (json_data['pages'][int(currentPage[1])]['id'] == currentPage[0]):
					properties = json_data['pages'][int(currentPage[1])]['questions']
					questionData = properties.itervalues().next()
					key = properties.keys()[int(currentPage[2])]
					if isinstance(rowType, tuple):
						if (questionNumber in multipleChoice):
							multipleChoice[questionNumber].append(unicode(row[1]))
						else:
							multipleChoice[questionNumber] = [unicode(row[1])]
					else:
						if (row[1] != questionData[rowType]):
							json_data['pages'][int(currentPage[1])]['questions'][key][rowType] = unicode(row[1])
			
		for array in multipleChoice:
			currentPage = getPage(array)
			properties = json_data['pages'][int(currentPage[1])]['questions']
			key = properties.keys()[int(currentPage[2])]
	
			if (currentPage[1] == 1):
				print json_data['pages'][int(currentPage[1])]['questions'][key]
			else:
				json_data['pages'][int(currentPage[1])]['questions'][key]['options'] = multipleChoice[array]

		with open(os.path.join(jsonFileDir, 'prereg-prize-test.json'), 'w') as newFile:
			json.dump(json_data, newFile)

if __name__ == '__main__':
    main()
    #print getPage('03')
    #print getPageIndex('page1')
