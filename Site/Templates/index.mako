<%include file="_header.mako" />
<% import Site.Settings %>
<div class="row">
    <div class="hero-unit">
        <h1>OSF launches public beta!</h1>
        <p style="margin-top: 6px;">
            % if not Site.Settings.local:
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

<div class="row">
    <div class="span4">
        <h2>OSF Features</h2>
            <p>
                <ol>
                    <li>Document and archive studies
                    <li>Share and find materials, scripts, data
                    <li>Detail individual contributions
                    <li>Increase transparency
                    <li>Time-stamp materials
                </ol>
            </p>
            <p><a class="btn" href="/project/4znZP/wiki/home">Learn More</a></p>
    </div>
    <div class="span4">
        <h2>Find Projects and Data</h2>
        <p>
            <p>Find background, materials and data for public projects.  Use search or see, for example, the <a href="/project/EZcUj/wiki/home">Reproducibility Project</a>&mdash;a large-scale, open collaboration investigating reproducibility of published findings.</p>
        </p>
    </div>
    <div class="span4">
      <h2>Get Involved</h2>
      <p>Scientists and developers can contribute.  Read more about OSF, join a project, subscribe to the discussion group, or just be a fan.</p>
      <p>
            <form action="http://groups.google.com/group/openscienceframework/boxsubscribe">
            <input type=hidden name="hl" value="en">
            <input class="span3" id="" name="email" type="text" placeholder="Join our email list" /><button type="submit" class="btn primary small">Join</button>
            </form>
            <a href="http://groups.google.com/group/openscienceframework?hl=en">Or visit our group</a>
            
        <br />
        <a href="http://facebook.com/openscienceframework">Open Science Framework on Facebook</a>
        	      <div class="fb-like" data-href="http://www.facebook.com/OpenScienceFramework" data-send="false" data-width="275" data-show-faces="false"></div></li>
                  <a href="https://twitter.com/OSFramework" class="twitter-follow-button" data-show-count="false" data-size="large">Follow @OSFramework</a>
                  % if not Site.Settings.local:
                  <script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js.id=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
                  %endif
      </p>
    </div>
</div>

<%include file="footer.mako" />
