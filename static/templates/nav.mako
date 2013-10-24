<nav class="navbar navbar-inverse navbar-fixed-top" role="navigation">
    <div class="container">
      <div class="navbar-header">
        <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
          <span class="sr-only">Toggle navigation</span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>
        <a class="navbar-brand" href="/">Open Science Framework<span class="brand-version"> BETA</span></a>
      </div><!-- end navbar-header -->

      <div class="collapse navbar-collapse navbar-ex1-collapse">
        <ul class="nav navbar-nav">
          %if user_name:
          <li><a rel="tooltip" title="My Dashboard" href="/dashboard/">Dashboard</a></li>
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
              <li><a href="/project/4znZP/wiki/home">About</a></li>
              <li><a href="/faq/">FAQ</a></li>
              <li><a href="/getting-started">Getting Started</a></li>
            </ul><!-- end dropdown-menu -->
          </li><!-- end dropdown -->
        </ul><!-- end nav navbar-nav -->
        <!-- Search bar -->
        <form class="navbar-form navbar-left" role="search">
          <div class="form-group">
            <input type="text" class="form-control search-query" placeholder="Search" name="q">
          </div>
        </form>
        <ul class="nav navbar-nav navbar-right">
          %if user_name and display_name:
          <li><a href="/profile">${display_name}</a></li>
          <li><a rel="tooltip" title="Settings" href="/settings"><span class="icon-cog"></span></a></li>
          <li><a rel='tooltip' title='Log out' href='/logout'><span class="icon-signout"></span></a></li>
          %else:
              %if allow_login:
              <a class="btn btn-primary navbar-btn" href="/account">Create an Account or Sign-In</a>
              %else:
              %endif
          %endif
        </ul><!-- end nav navbar-nav navbar-right -->
      </div><!-- end navbar-collapse -->
    </div><!-- end container-->
</nav>
