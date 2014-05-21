# -*- coding: utf-8 -*-
import re

from webtest import response


class TestResponse(response.TestResponse):
    '''Same as WebTest's TestResponse but adds basic HTTP authentication to
    ``click`` and ``clickbutton``.
    '''

    def click(self, description=None, linkid=None, href=None,
              index=None, verbose=False,
              extra_environ=None, auth=None):
        """
        Click the link as described.  Each of ``description``,
        ``linkid``, and ``url`` are *patterns*, meaning that they are
        either strings (regular expressions), compiled regular
        expressions (objects with a ``search`` method), or callables
        returning true or false.

        All the given patterns are ANDed together:

        * ``description`` is a pattern that matches the contents of the
          anchor (HTML and all -- everything between ``<a...>`` and
          ``</a>``)

        * ``linkid`` is a pattern that matches the ``id`` attribute of
          the anchor.  It will receive the empty string if no id is
          given.

        * ``href`` is a pattern that matches the ``href`` of the anchor;
          the literal content of that attribute, not the fully qualified
          attribute.

        If more than one link matches, then the ``index`` link is
        followed.  If ``index`` is not given and more than one link
        matches, or if no link matches, then ``IndexError`` will be
        raised.

        If you give ``verbose`` then messages will be printed about
        each link, and why it does or doesn't match.  If you use
        ``app.click(verbose=True)`` you'll see a list of all the
        links.

        You can use multiple criteria to essentially assert multiple
        aspects about the link, e.g., where the link's destination is.
        """
        found_html, found_desc, found_attrs = self._find_element(
            tag='a', href_attr='href',
            href_extract=None,
            content=description,
            id=linkid,
            href_pattern=href,
            index=index, verbose=verbose)
        auth = auth or self.test_app.auth
        return self.goto(str(found_attrs['uri']), extra_environ=extra_environ,
                        auth=auth)

    def clickbutton(self, description=None, buttonid=None, href=None,
                    index=None, verbose=False, auth=None):
        """
        Like :meth:`~webtest.response.TestResponse.click`, except looks
        for link-like buttons.
        This kind of button should look like
        ``<button onclick="...location.href='url'...">``.
        """
        found_html, found_desc, found_attrs = self._find_element(
            tag='button', href_attr='onclick',
            href_extract=re.compile(r"location\.href='(.*?)'"),
            content=description,
            id=buttonid,
            href_pattern=href,
            index=index, verbose=verbose)
        auth = auth or self.test_app.auth
        return self.goto(str(found_attrs['uri']), auth=auth)
