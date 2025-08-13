## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako" />
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Hello ${user_fullname},
        <br><br>
        Congratulations on making a public project on OSF! Now that your project “${project_title}" is public, you’ll be able to take advantage of more OSF features:
        <ul>
            <li><a href="${osf_url}${nid}/files/">The number of downloads of your files will be automatically logged for you</a></li>
            <li><a href="${osf_url}${nid}/analytics/">You can see analytics on how many others are accessing your projects</a></li>
            <li><a href="${osf_url}${nid}/">Visitors to your project can cite your work using the citation widget on your project’s page</a></li>
        </ul>
        <br>
        <br>
        If you would like to learn more about how to take advantage of any of these features, visit our <a href="https://help.osf.io" target="_blank" rel="noreferrer">Guides</a>.</a>.
        <br><br>
        Sincerely,
        <br>
        The OSF Team

    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${osf_url}">OSF</a> is provided as a free, open source service from the <a href="https://cos.io/">Center for Open Science</a>.
</%def>
