import nose

from nose.tools import *

from website.addons.dataverse.views.crud import scrape_dataverse


def test_scrape_dataverse():
    content = scrape_dataverse(2362170)
    assert_not_in('IQSS', content)
    assert_in('%esp', content)

if __name__=='__main__':
    nose.run()