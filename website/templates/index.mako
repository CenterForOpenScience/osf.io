<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
<div class="container" style="margin-top: 30px;">
<div class="row">
    <div class="col-md-4">
        <h1>Scientists</h1>
            <iframe style="padding-top: 20px;padding-right: 0px;padding-left: 0px;padding-bottom: 20px;" width="277" height="156" src="//www.youtube.com/embed/c6lCJFSnMcg" frameborder="0" allowfullscreen></iframe>
        <p>Scientists can use OSF for free to archive, share, find, register research materials and data. Watch the videos, get <a href="/project/4znZP/wiki/home">background info</a>, get <a href="/getting-started">help</a>, or just <a href="/account">register</a> to get started.</p>
    </div>
    <div class="col-md-4">
        <h1>Journals, Funders, and Societies</h1>
            <p style="padding-top: 25px;">Journals, funders and scientific societies can use the OSF as back-end infrastructure for preregistration, data and materials archiving, and other administrative functions. Email contact@centerforopenscience.org.</p>
        <a href="/explore/activity/"><img style="padding-top: 20px; padding-bottom:36px;" src="/static/img/activity.png" alt="public activity screenshot"></a>
    </div>
    <div class="col-md-4">
      <h1>Developers</h1>
        <iframe style="padding-top: 20px;padding-right: 0px;padding-left: 0px;padding-bottom: 20px;" width="277" height="156" src="//www.youtube.com/embed/WRadGRdkAIQ" frameborder="0" allowfullscreen></iframe>
      <p>Developers can contribute to OSF and other open-source projects, or connect their projects to OSF via API. To learn more you can watch the above video from SciPy, find us on <a href="https://github.com/centerforopenscience" target="_blank">GitHub</a>, or contact developer@centerforopenscience.org.</p>
        </div>
                  % if use_cdn:
                  <script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js._primary_key=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
                  %endif
      </p>
    </div>
</div>
</%def>

