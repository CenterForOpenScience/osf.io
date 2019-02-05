## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
    <br>
        Hello ${fullname},
        <br><br>
        Thanks for sharing ${title} on ${provider_name}.
        Sharing your research doesn’t have to stop there. Add supplemental files such as data, code, protocols, and other materials that comprise your ${preprint_word} to help others get the most from your research.
        Supplemental files will be stored in an OSF project that connects to your ${preprint_word}. Just edit your ${preprint_word}, and follow the instructions below:
        <br>
        > <a href="http://help.osf.io/m/preprints/l/664307-edit-your-preprint#create-a-new-osf-project">Upload supplemental files to a new OSF project</a>.
        > <a href="http://help.osf.io/m/preprints/l/664307-edit-your-preprint#connect-an-existing-osf-project">Upload supplemental files to a new OSF project</a>.
        <br><br>
        Sincerely,<br>
        Your ${provider_name} and OSF Team

    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${osf_url}">Open Science Framework</a> is provided as a free, open source service from the <a href="https://cos.io/">Center for Open Science</a>.
</%def>
