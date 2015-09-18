## -*- coding: utf-8 -*-
<%inherit file="notify_base.mako"/>
<%def name="content()">
    <div style="margin: 40px;">
        <br>
        <br>
        Hello ${fullname},
        <br>
        Congratulations on making a public project on the Open Science Framework (OSF)! Now that your project “${project_title}" is public, you’ll be able to take advantage of more OSF features:
        <ul>
            <li><a href="http://osf.io/${nid}/files/">The number of downloads of your files will be automatically logged for you</a></li>
            <li><a href="http://osf.io/${nid}/settings/">You can enable other OSF users to comment on your work</a></li>
            <li><a href="http://osf.io/${nid}/">Visitors to your project can cite your work using the citation widget on your project’s page</a></li>
        </ul>
        <br>
        <a href="https://twitter.com/share" class="twitter-share-button" data-url="http://osf.io/${nid}/" data-text="Check out my project on the Open Science Framework!" data-count="none">Tweet</a>
        <script>
            !function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0],p=/^http:/.test(d.location)?'http':'https';if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src=p+'://platform.twitter.com/widgets.js';fjs.parentNode.insertBefore(js,fjs);}}(document, 'script', 'twitter-wjs');
        </script>
        <br>
        If you would like to learn more about how to take advantage of any of these features, visit our <a href="https://osf.io/getting-started/#start">Getting Started page</a> or <a href="mailto:support@osf.io">drop us a line</a>.
        <br><br>
        Best wishes,
        <br>
        COS Support Team
    </div>
</%def>
<%def name="footer()">
    <div>
        The <a href="http://osf.io">Open Science Framework</a> is provided as a free, open-source service from the
        <a href="http://cos.io/">Center for Open Science</a>.
    </div>
</%def>
