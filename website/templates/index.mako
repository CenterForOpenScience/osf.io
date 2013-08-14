<%include file="_header.mako" />
<% import website.settings %>
<div class="row">
    <div class="hero-unit">
        <h1>OSF launches public beta!</h1>
        <p style="margin-top: 6px;">
            % if website.settings.use_cdn_for_client_libs:
                <iframe width="853" height="480" src="http://www.youtube.com/embed/c6lCJFSnMcg" frameborder="0" allowfullscreen></iframe>
            %else:
                <img src="/static/youtube.png" width="853" height="480" />
            %endif
        </p>
        ##<p style="size: 12px;">The Open Science Framework (OSF) is an infrastructure for documenting, archiving, logging, sharing, and registering scientific projects.  Tools are being designed to integrate open practices with a scientist's daily workflow rather than appending them ex post facto. The OSF is a member project of and the infrastructure that supports the Open Science Collaboration (OSC)&mdash;an open collaboration of scientists. The overall goal of both the OSF and OSC is to increase the alignment between scientific values and scientific practices.</p>
##        <p>This group is dedicated to creating a set of tools to improve a scientist's workflow and decrease the gap between scientific values and scientific practices.  An on-line study registry tool will document the scientific process, facilitate sharing, increase transparency, and distinguish between confirmatory and exploratory research.  These tools will connect with existing technologies that complement and support the scientific workflow.  We aim to encourage collaboration and open ideals at every stage of the scientific process.</p>
##        <p>While we are completing the beta release of the study registry, we welcome discussion and collaboration on these topics and hope you will join us on our mailing list/forum:</p>
        <p>
            <a class="btn primary large" href="/account">Get started</a>
            <a class="btn primary large" href="/project/4znZP/wiki/home">Learn more about the OSF</a>
            <a class="btn primary large" href="/project/VMRGu/wiki/home">Learn more about the OSC</a>
            <a class="btn primary large" href="http://groups.google.com/group/openscienceframework">Join the Discussion &raquo;</a></p>
    </div>
</div>

</div>
<div class="container" style="margin-top: 40px;">
<div class="row">
    <div class="span4">
        <h1>Scientists</h1>
            <iframe style="padding-top: 20px;padding-right: 0px;padding-left: 0px;padding-bottom: 20px;" width="277" height="156" src="//www.youtube.com/embed/c6lCJFSnMcg" frameborder="0" allowfullscreen></iframe>
        <p>Scientists can use OSF for free to archive, share, find, register research materials and data. Watch the videos, get <a href="http://openscienceframework.org/project/4znZP/wiki/home">background info</a>, get <a href="/getting-started">help</a>, or just <a href="http://openscienceframework.org/account">register</a> to get started.</p>
    </div>
    <div class="span4">
        <h1>Journals, Funders, and Societies</h1>
            <p style="padding-top: 25px;">Journals, funders and scientific societies can use the OSF as back-end infrastructure for preregistration, data and materials archiving, and other administrative functions. Email contact@centerforopenscience.org.</p>
        <a href="http://openscienceframework.org/explore/activity/"><img style="padding-top: 20px; padding-bottom:36px;" src="/static/img/activity.png" alt="public activity screenshot"></a>
    </div>
    <div class="span4">
      <h1>Developers</h1>
        <iframe style="padding-top: 20px;padding-right: 0px;padding-left: 0px;padding-bottom: 20px;" width="277" height="156" src="//www.youtube.com/embed/WRadGRdkAIQ" frameborder="0" allowfullscreen></iframe>
      <p>Developers can contribute to OSF and other open-source projects, or connect their projects to OSF via API. Watch the above video from SciPy, visit our <a href="https://github.com/centerforopenscience">GitHub page</a>, or contact developer@centerforopenscience.org.</p>
        </div>
                  % if website.settings.use_cdn_for_client_libs:
                  <script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
                  %endif
      </p>
    </div>
</div>

<%include file="footer.mako" />
