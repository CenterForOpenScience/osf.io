## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Hello ${user.fullname},
        Best wishes,
        <br>
        COS Support Team
    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${osf_url}">OSF</a> is provided as a free, open source service from the <a href="https://cos.io/">Center for Open Science</a>.
</%def>
