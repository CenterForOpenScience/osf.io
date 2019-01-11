## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        Hello ${fullname},
        <br><br>
        Congratulations on making a public project on the GakuNin RDM (GRDM)! Now that your project “${project_title}" is public, you’ll be able to take advantage of more GakuNin RDM features:
        <ul>
            <li><a href="${osf_url}${nid}/files/">The number of downloads of your files will be automatically logged for you</a></li>
            <li><a href="${osf_url}${nid}/analytics/">You can see analytics on how many others are accessing your projects</a></li>
            <li><a href="${osf_url}${nid}/">Visitors to your project can cite your work using the citation widget on your project’s page</a></li>
        </ul>
        <a href="https://twitter.com/share" class="twitter-share-button" data-url="${osf_url}${nid}/" data-text="Check out my project on the GakuNin RDM!" data-count="none">Tweet</a>
        <br>
        <script>
            !function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+'://platform.twitter.com/widgets.js';fjs.parentNode.insertBefore(js,fjs);}}(document, 'script', 'twitter-wjs');
        </script>
        <br>
        If you would like to learn more about how to take advantage of any of these features, visit our <a href="https://meatwiki.nii.ac.jp/confluence/display/gakuninrdmusers" target="_blank" rel="noreferrer">Guides</a> or <a href="mailto:${osf_support_email}">drop us a line</a>.
        <br><br>
        Best wishes,
        <br>
        NII Support Team

    </div>
</%def>
<%def name="footer()">
    <br>
    The <a href="${osf_url}">GakuNin RDM</a> is provided as a free, open source service from the <a href="https://nii.ac.jp/">National Institute of Informatics</a>.
</%def>
