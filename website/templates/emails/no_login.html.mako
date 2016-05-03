## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Hello ${fullname},
        <br><br>
        We’ve noticed it’s been a while since you used the Open Science Framework (OSF). We are constantly adding and improving features, so we thought it might be time to check in with you.
        Most researchers begin using the OSF by creating a project to organize their files and notes. Projects are equipped with powerful features to help you manage your research:
        <br>
        <ul>
            <li>You can keep your work private, or make it public and share it with others</li>
            <li>You can use the wiki to live-edit content with your collaborators</li>
            <li>You can connect to third-party services like Dropbox or Google Drive</li>
        </ul>
        To get started now, visit your dashboard and click on “Create a project.”
        If you have specific questions, or would like to set up a free training session for you and your colleagues, please do not hesitate to <a href="mailto:support@osf.io">get in touch with us!</a>
        <br><br>
        Best,
        <br>
        COS Support Team
    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${osf_url}">Open Science Framework</a> is provided as a free, open source service from the <a href="http://cos.io/">Center for Open Science</a>.
</%def>
