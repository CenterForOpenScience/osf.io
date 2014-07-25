<nav class="navbar navbar-inverse navbar-fixed-top" role="navigation">
    <div class="container">
      <div class="navbar-header">
        <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
          <span class="sr-only">Toggle navigation</span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>
        <a class="navbar-brand visible-lg visible-md" href="/">Open Science Framework<span class="brand-version"> BETA</span></a>
        <a class="navbar-brand visible-sm visible-xs" href="/">OSF</a>
      </div><!-- end navbar-header -->

      <div class="collapse navbar-collapse navbar-ex1-collapse">
        <ul class="nav navbar-nav">
          <li class="visible-xs"><a href="/">Home</a></li>
          %if user_name:
          <li><a rel="tooltip" title="My Dashboard" href="${ web_url_for('dashboard') }">My Dashboard</a></li>
          %endif
          <li class="dropdown">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown">Explore <b class="caret"></b></a>
            <ul class="dropdown-menu">
              <li><a href="/explore">Collaborator Network</a></li>
              <li><a href="/explore/activity">Public Activity</a></li>
            </ul><!-- end dropdown-menu -->
          </li><!-- end dropdown -->
          <li class="dropdown">
            <a href="#" class="dropdown-toggle" data-toggle="dropdown">Help <b class="caret"></b></a>
            <ul class="dropdown-menu">
              <li><a href="/4znZP/wiki/home">About</a></li>
              <li><a href="/faq/">FAQ</a></li>
              <li><a href="/getting-started">Getting Started</a></li>
              <li><script type="text/javascript">document.write("<n uers=\"znvygb:fhccbeg@bfs.vb\" ery=\"absbyybj\">Rznvy Fhccbeg</n>".replace(/[a-zA-Z]/g,function(e){return String.fromCharCode((e<="Z"?90:122)>=(e=e.charCodeAt(0)+13)?e:e-26)}));</script><noscript>Email Support: <span class="obfuscated-email-noscript"><strong><u>supp<span style="display:none;">null</span>ort@<span style="display:none;">null</span>osf.<span style="display:none;">null</span>io</u></strong></span></noscript></li>
              <li><script type="text/javascript">document.write("<n uers=\"znvygb:pbagnpg@bfs.vb\" ery=\"absbyybj\">Pbagnpg</n>".replace(/[a-zA-Z]/g,function(e){return String.fromCharCode((e<="Z"?90:122)>=(e=e.charCodeAt(0)+13)?e:e-26)}));</script><noscript>Contact OSF: <span class="obfuscated-email-noscript"><strong><u>cont<span style="display:none;">null</span>act@<span style="display:none;">null</span>osf.<span style="display:none;">null</span>io</u></strong></span></noscript></li>
            </ul><!-- end dropdown-menu -->
          </li><!-- end dropdown -->
        </ul><!-- end nav navbar-nav -->
        <!-- Search bar -->
        <form id="searchBar" class="navbar-form navbar-left hidden-xs" action="${ web_url_for('search_search') }" method="get" role="search">
          <div class="form-group">
            <input type="text" class="form-control search-query" placeholder="Search" name="q">
          </div>
        </form>
        <ul class="nav navbar-nav navbar-right">
          %if user_name and display_name:
          <li rel="tooltip" title="${user_name}">
            <a class="hidden-lg" href="/profile/">
              <span class="icon-user"></span>
            </a>
            <a class="visible-lg"href="/profile/">
              <span>${display_name}</span>
            </a>
          </li>
          <li><a rel="tooltip" title="Settings" href="${ web_url_for('user_profile') }"><span class="icon-cog"></span></a></li>
          <li><a rel="tooltip" title="Log out" href="${ web_url_for('auth_logout') }"><span class="icon-signout"></span></a></li>
          %else:
              %if allow_login:
              <a class="btn btn-primary navbar-btn" href="${ web_url_for('auth_login') }">Create an Account or Sign-In</a>
              %else:
              %endif
          %endif
        </ul><!-- end nav navbar-nav navbar-right -->
      </div><!-- end navbar-collapse -->
    </div><!-- end container-->
</nav>
