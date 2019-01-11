## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
    <br>
        Hello ${fullname},
        <br><br>
        Do you use storage services like Dropbox, GitHub, or Google Drive to keep track of your research materials?
        the GakuNin RDM (GRDM) makes it easy to integrate various research tools you already use by allowing
        you to connect them as an add-on to the GakuNin RDM. When you connect an add-on, you can manage files from either the
        GakuNin RDM or external storage services. Files will be synced whenever you make changes.
        Get more information on GakuNin RDM add-ons.
        <br><br>
        Link your accounts today: <a href="${osf_url}settings">https://rdm.nii.ac.jp/settings</a>.
        <br><br>
        Best wishes,<br>
        NII Support Team

    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${osf_url}">GakuNin RDM</a> is provided as a free, open source service from the <a href="https://nii.ac.jp/">National Institute of Informatics</a>.
</%def>
