import re

product_line_pattern = re.compile(r'^#product[.](.+)$')

def match_product_line(str):
    return re.match(product_line_pattern, str)

def is_valid_product_line(match):
    return match is not None and len(match.groups()) == 1

def product_name_key(product_name):
    head_char = product_name[0]
    return head_char.upper() if head_char.isalpha() else '_'


def gen_product_name_list(product_name_filepath):
    product_name_list = []
    with open(product_name_filepath) as f:
        for line in f:
            match = re.match(product_line_pattern, line)
            if(is_valid_product_line(match)):
                product_name_list.append(match.group(1))
    return product_name_list
