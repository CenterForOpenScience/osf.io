import helper

import framework.status as status
from mako.template import Template
from mako.lookup import TemplateLookup
from website import settings
from website import filters

makolookup = TemplateLookup(directories=helper.get_directories(['./website']))

def render(filename, **kwargs):
    tidy = None
    prettify = None
    collapse_whitespace = None
    
    if 'prettify' in kwargs:
        if kwargs['prettify']:
            prettify = True
        del kwargs['prettify']
    
    if 'tidy' in kwargs:
        if kwargs['tidy']:
            tidy = True
            prettify = None
        del kwargs['tidy']
    
    if 'collapse_whitespace' in kwargs:
        if kwargs['collapse_whitespace']:
            prettify = None
            tidy = None
            collapse_whitespace = True
        del kwargs['collapse_whitespace']
        
    if not 'includejs' in kwargs:
        kwargs['includejs'] = []
    
    kwargs['status'] = status.pop_status_messages()

    kwargs['settings'] = settings
    kwargs['filters'] = filters

    t = makolookup.get_template(filename).render(**kwargs)

    #if tidy:
    #    import tidy
    #    options = dict(output_xhtml=1, add_xml_decl=1, indent=1, tidy_mark=0)
    #    return tidy.parseString(t, **options)
    
    if prettify:
        pass
        # from BeautifulSoup import BeautifulSoup
        # soup = BeautifulSoup(t)
        # return soup.prettify()
    
    if collapse_whitespace:
        return ' '.join(t.split())
    
    return t