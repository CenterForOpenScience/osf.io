<%block name="nav">
<link rel="stylesheet" href='/static/css/nav.css'>
<div class="osf-nav-wrapper">

<nav class="navbar navbar-inverse navbar-fixed-top" id="navbarScope" role="navigation">
    <div class="container">
    <div class="navbar-header">
      <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#navbar" aria-expanded="false" aria-controls="navbar">
        <span class="sr-only">Toggle navigation</span>
        <span class="icon-bar"></span>
        <span class="icon-bar"></span>
        <span class="icon-bar"></span>
      </button>
      <!-- ko ifnot: onSearchPage -->
      <span class="visible-xs" data-bind="click : toggleSearch, css: searchCSS">
          <a class="osf-xs-search pull-right" style="padding-top: 12px" >
            <span rel="tooltip" data-placement="bottom" title="Search OSF" class="fa fa-search fa-lg fa-inverse" ></span>
          </a>
      </span>
      <!-- /ko -->
      <a class="navbar-brand hidden-sm hidden-xs" href="/"><img src="/static/img/cos-white2.png" class="osf-navbar-logo" width="27" alt="COS logo"/> Open Science Framework</a>
      <a class="navbar-brand visible-sm visible-xs" href="/"><img src="/static/img/cos-white2.png" class="osf-navbar-logo" width="27" alt="COS logo"/> OSF</a>
    </div>
    <div id="navbar" class="navbar-collapse collapse navbar-right">
      <ul class="nav navbar-nav">
        % if user_name:
            <li id="osfNavDashboard"><a href="/dashboard">Dashboard</a></li>
            <li id="osfNavMyProjects"><a href="/myprojects/">My Projects</a></li>
        % endif
        <li class="dropdown">
          <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-expanded="false">Browse <span class="caret"></span></a>
          <ul class="dropdown-menu" role="menu">
              <li><a href="${domain}explore/activity/">New Projects</a></li>
              <li><a href="${domain}search/?q=*&amp;filter=registration">Registry</a></li>
              <li><a href="${web_url_for('conference_view', _absolute=True)}">Meetings</a></li>
          </ul>
        </li>
        % if not user_name:
        <li class="dropdown">
          <a href="${domain}support/" >Support</a>
        </li>
        % endif

        <!-- ko ifnot: onSearchPage -->
        <li class="hidden-xs" data-bind="click : toggleSearch, css: searchCSS">
            <a class="" >
                <span rel="tooltip" data-placement="bottom" title="Search OSF" class="fa fa-search fa-lg" ></span>
            </a>
        </li>
        <!-- /ko -->
        % if user_name and display_name:
        <li class="dropdown">
          <a href="#" class="dropdown-toggle nav-user-dropdown" data-toggle="dropdown" role="button" aria-expanded="false"><span class="osf-gravatar"><img src="${user_gravatar}" alt="User gravatar"/> </span> ${display_name} <span class="caret"></span></a>
          <ul class="dropdown-menu" role="menu">
              <li>
                  <a href="/profile/"><i class="fa fa-user fa-lg p-r-xs"></i> My Profile</a>
              </li>
              <li>
                  <a href="/support/" ><i class="fa fa-life-ring fa-lg p-r-xs"></i> Support</a>
              </li>

              <li>
                  <a href="${web_url_for('user_profile')}"><i class="fa fa-cog fa-lg p-r-xs"></i> Settings</a>
              </li>
              <li>
                  <a href="${web_url_for('auth_logout')}"><i class="fa fa-sign-out fa-lg p-r-xs"></i> Log out</a>
              </li>

          </ul>
        </li>
        % elif allow_login:
            %if institution:
                 <li class="dropdown sign-in" data-bind="with: $root.signIn">
                  <div class="btn-group">
                      <a href="${domain}login/?campaign=institution&redirect_url=${redirect_url}">
                        <button type="button" class="btn btn-info btn-top-login">
                          Sign in <span class="hidden-xs"><i class="fa fa-arrow-right"></i></span>
                        </button>
                      </a>
                </div>
                </li>
            %else :
            <li class="dropdown sign-in" data-bind="with: $root.signIn">
                <div class="col-sm-12">
                    <a href="${web_url_for('auth_login')}?sign_up=True" class="btn btn-success btn-top-signup m-r-xs">Sign up</a>
                    <button type="button" class="btn btn-info btn-top-login p-sm dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
                        Sign in <span class="caret hidden-xs"></span>
                    </button>
                    <ul class="dropdown-menu" id="menuLogin" role="menu">
                        <form class="form" id="signInForm" data-bind="submit: submit" action="${login_url}" method="POST">
                            <div class="form-group"><input id="email" class="form-control" type="email" data-bind="value: username" name="username" placeholder="Email" aria-label="Username"></div>
                            <div class="form-group"><input name="password" id="password" class="form-control" type="password" placeholder="Password" data-bind="value: password" aria-label="Password"></div>
                            <div class="form-group"><button type="submit" id="btnLogin" class="btn btn-block btn-primary">Login</button></div>
                            %if enable_institutions:
                                <div class="text-center m-b-sm"> <a href="/login/?campaign=institution">Login through your institution  <i class="fa fa-arrow-right"></i></a></div>
                            %endif
                            <div class="text-center m-b-sm"> <a href="/forgotpassword/">Forgot password?</a></div>
                        </form>
                    </ul>
                </div>
            </li>
             %endif
        % endif
          </ul>
    </div><!--/.navbar-collapse -->
    </div>


</nav>
    <!-- ko ifnot: onSearchPage -->
        <%include file='./search_bar.mako' />
    <!-- /ko -->
</div>
</%block>
