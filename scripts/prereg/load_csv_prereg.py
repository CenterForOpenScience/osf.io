""" Load pre-reg questions into schema from csv file
"""

import os
import sys
import csv
import json
import logging

from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_page(quest_num):
    """ Given a question number, returns list containing page id, page index, and index of question on page
    ['page1', 0, 1] => Question 2 on page 1
    """
    pages = {
        'page1': ['01', '02', '03', '04'],
        'page2': ['05', '06', '07', '08'],
        'page3': ['09', '10', '11', '12', '13', '14', '15'],
        'page4': ['16', '17', '18', '19', '20', '21'],
        'page5': ['22']
    }
    for page in pages:
        for question in pages[page]:
            if quest_num == question:
                question_index = pages[page].index(question)
                page_index = int(page.replace('page', '')) - 1  # 'page1' => 1
                return [page, page_index, question_index]
    return False

def get_label(row_type):
    """ Translates the csv terms to json schema terms used"""
    types = {'QUESTION': 'title', 'EXPLAIN': 'description', 'HELP': 'help', 'NAV': 'nav'}

    for type in types:
        if type == row_type:
            return types[type]

        elif row_type.startswith('MC'):
            mc = row_type.split('C')
            index = int(mc[1]) - 1;
            return (mc[1], index)

# use json.dump(<data>, <filename>) to write formatted json to file
def main(dry_run=True):
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

    prereg_content = os.path.join(__location__, 'preregcontent.csv');
    schema_directory = os.path.realpath(os.path.join(os.getcwd(), 'website/project/metadata'))
    prereg_schema = os.path.join(schema_directory, 'prereg-prize-test.json')

    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info('Opening the Prereg JSON Schema')

    with open(prereg_schema) as json_file:
        json_data = json.load(json_file)
        multiple_choice = {}

        with open(prereg_content, 'rU') as csv_file:
            cr = csv.reader(csv_file)
            cr.next()
            previous_question = ''
            current_page = ''

            # row: ['01_QUESTION', 'What is your plan?']
            for row in cr:
                # label: ['01' 'QUESTION']
                label = row[0].split('_')
                question_num = label[0]
                question_part = label[1]

                if previous_question != question_num:
                    previous_question = question_num
                    current_page = get_page(question_num)

                row_type = get_label(question_part)

                if json_data['pages'][int(current_page[1])]['id'] == current_page[0]:
                    # dict of each question in a page
                    questions = json_data['pages'][int(current_page[1])]['questions']
                    question_data = questions.itervalues().next()
                    key = sorted(questions.keys())[int(current_page[2])]

                    # row is a multiple choice question
                    if isinstance(row_type, tuple):
                        if question_num in multiple_choice:
                            multiple_choice[question_num].append(unicode(row[1]))
                        else:
                            multiple_choice[question_num] = [unicode(row[1])]
                    else:
                        # If the csv and json differ, save it
                        if row[1] != question_data[row_type]:
                            json_data['pages'][int(current_page[1])]['questions'][key][row_type] = unicode(row[1])

            for list in multiple_choice:
                current_page = get_page(list)
                questions = json_data['pages'][int(current_page[1])]['questions']
                key = questions.keys()[int(current_page[2])]

                if current_page[1] != 1:
                    json_data['pages'][int(current_page[1])]['questions'][key]['options'] = multiple_choice[list]

        if not dry_run:
            with open(os.path.join(schema_directory, 'prereg-prize-test.json'), 'w') as updated_file:
                json.dump(json_data, updated_file, indent=4)
        else: # For tests
            with open(os.path.join(schema_directory, 'prereg-prize-test.test.json'), 'w') as updated_file:
                json.dump(json_data, updated_file, indent=4)

if __name__ == '__main__':
    dry_run ='dry' in sys.argv
    main(dry_run)
