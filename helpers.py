import re


def enum_name_to_str(enum_name):
    ''' converts an uppercase enum name to a sentence case string '''
    # replace _ with space
    return enum_name.replace("_", " ").title()


def camel_case_to_sent_case(camel_str):
    ''' convert a camel case string to a sentence case string '''
    return re.sub("(\B[A-Z])", " \\1", camel_str)
