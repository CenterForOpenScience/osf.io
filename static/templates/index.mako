<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>

      <div class="headline">
        <div class="container">
          <h1>The Open Science Framework</h1>
          <h2 class="tagline">Manage, share, and discover research.</h2>
        </div>
        </div>
        <div class="row">
          <div class="col-lg-1 centered">
        % if not user_name:
            <a href="/account/" class="btn btn-xl btn-success">Sign up</a>
        % else:
            <a href="/dashboard/" class="btn btn-xl btn-info">Go to Dashboard</a>
        % endif
          </div>
        </div>
      <hr class="featurette-divider">

      <div class="featurette" id="about">
            <iframe class="featurette-image pull-right" height="312" width="554" src="//www.youtube.com/embed/c6lCJFSnMcg" frameborder="0" allowfullscreen></iframe>
        <h2 class="featurette-heading">Scientists</h2>
        <p class="lead">Scientists can use OSF for free to archive, share, find, register research materials and data. Watch the videos, get <a href="/project/4znZP/wiki/home">background info</a>, get <a href="/getting-started">help</a>, or just <a href="/account">register</a> to get started.</p>
      </div>

      <hr class="featurette-divider">

      <div class="featurette" id="services">
        <a href="/explore/activity/">
        <img class="featurette-image pull-left"  width="450" height="200" src="/static/img/activity.png"></a>
        <h2 class="featurette-heading">Journals, Funders, and Societies</h2>
        <p class="lead">Journals, funders and scientific societies can use the OSF as back-end infrastructure for preregistration, data and materials archiving, and other administrative functions. Email <a href="mailto:contact@centerforopenscience.org">contact@centerforopenscience.org.</a></p>
      </div>

      <hr class="featurette-divider">

      <div class="featurette" id="contact">
        <iframe class="featurette-image pull-right" height="312" width="554" src="//www.youtube.com/embed/WRadGRdkAIQ" frameborder="0" allowfullscreen></iframe>
        <h2 class="featurette-heading">Developers</h2>
        <p class="lead">Developers can contribute to OSF and other open-source projects, or connect their projects to OSF via API. To learn more you can watch the above video from SciPy, find us on <a href="https://github.com/centerforopenscience" target="_blank">GitHub</a>, or contact <a href="mailto:developer@centerforopenscience.org"> developer@centerforopenscience.org.</a></p>
      </div>
      % if use_cdn:
      <script>!function(d,s,id){var js,fjs=d.getElementsByTagName(s)[0];if(!d.getElementById(id)){js=d.createElement(s);js._primary_key=id;js.src="//platform.twitter.com/widgets.js";fjs.parentNode.insertBefore(js,fjs);}}(document,"script","twitter-wjs");</script>
      %endif

<div mod-meta='{"tpl":"footer.mako","replace": true}'></div>
