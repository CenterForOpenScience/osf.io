## -*- coding: utf-8 -*-
<%inherit file="notify_base.html"/>
<%def name="content()">
<p>
    Hello ${fullname},
    Do you use storage services like Dropbox, GitHub, or Google Drive to keep track of your research materials?
    The Open Science Framework (OSF) makes it easy to integrate various research tools you already use by allowing
    you to connect them as an add-on to the OSF. When you connect an add-on you can manage files from either the
    OSF or external storage services. Files will be synced whenever you make changes.
    Get more information on OSF add-ons.
    Link your accounts today: <a href="http://osf.io/settings">http://osf.io/settings</a>.
    Best wishes,
    COS Support Team
</p>
</%def>
<%def name="footer()">
<p>The <a href="http://osf.io">Open Science Framework</a> is provided as a free, open-source service from the
    <a href="http://cos.io/">Center for Open Science</a>.
</p>
</%def>
