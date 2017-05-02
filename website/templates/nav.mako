<%block name="nav">
<link rel="stylesheet" href='/static/css/nav.css'>
<div class="osf-nav-wrapper">

<nav class="navbar navbar-inverse navbar-fixed-top" id="navbarScope" role="navigation">
    <div class="container">
        <div class="navbar-header">
            <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#secondary-navigation" aria-label="Toggle secondary navigation"}}>
                <span class="sr-only">Toggle navigation</span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
            </button>
        <a class="navbar-brand" href="/" aria-label="Go home"><span class="osf-navbar-logo"></span> OSF </a>
        <div class="dropdown primary-nav">
            <button id="primary-navigation" class="dropdown-toggle btn-link" data-toggle="dropdown" role="button" aria-expanded="false" aria-label="Toggle primarnavigation">
                <span class="fa fa-caret-down fa-2x"></span>
            </button>
            <ul class="dropdown-menu service-dropdown" role="menu">
                <li><a href="${domain}">OSF<b>HOME</b></a></li>
                <li><a href="${domain}preprints/">OSF<b>PREPRINTS</b></a></li>
                <li><a href="${domain}registries/">OSF<b>REGISTRIES</b></a></li>
                <li><a href="${domain}meetings/">OSF<b>MEETINGS</b></a></li>
            </ul>
        </div>
        <div class="service-name">
            <a href="${domain}"><strong data-bind="text: osfServices[currentService].name"></strong></a>
        </div>
    </div>
    <div id="navbar" class="navbar-collapse collapse navbar-right">
        <ul class="nav navbar-nav"></ul>
    </div><!--/.navbar-collapse -->

    <div class="navbar-collapse collapse navbar-right" id="secondary-navigation">
        <ul class="nav navbar-nav">
            <!-- ko if: currentService === 'home' -->
            % if user_name:
                <li><a href="${domain}myprojects/">My Projects</a></li>
            % endif
                <li><a href="${domain}search/">Search OSF</a></li>
            <!-- /ko -->

            % if not user_name:
            <li class="dropdown">
            <a href="${domain}support/" >Support</a>
            </li>
            % endif

            % if user_name and display_name:
            <li class="dropdown">
            <button class="dropdown-toggle nav-user-dropdown btn-link" data-toggle="dropdown" role="button" aria-expanded="false" aria-label="Toggle auth dropdown">
                <span class="osf-gravatar">
                    <img src="${user_gravatar}" alt="User gravatar">
                </span> ${display_name}
                <span class="caret"></span>
            </button>

            <ul class="dropdown-menu auth-dropdown" role="menu">
                <li><a href="${domain}profile/"><i class="fa fa-user fa-lg p-r-xs"></i> My Profile</a></li>
                <li><a href="${domain}support/" ><i class="fa fa-life-ring fa-lg p-r-xs"></i> OSF Support</a></li>
                <li><a href="${web_url_for('user_profile')}"><i class="fa fa-cog fa-lg p-r-xs"></i> Settings</a></li>
                <li><a href="${web_url_for('auth_logout')}"><i class="fa fa-sign-out fa-lg p-r-xs"></i> Log out</a></li>
            </ul>
            </li>
            % elif allow_login:
                %if institution:
                    <li class="dropdown sign-in">
                    <div class="btn-group">
                        <a href="${domain}login/?campaign=institution&redirect_url=${redirect_url}">
                            <button type="button" class="btn btn-info btn-top-login">
                            Sign in <span class="hidden-xs"><i class="fa fa-arrow-right"></i></span>
                            </button>
                        </a>
                    </div>
                    </li>
                %else :
                <li class="dropdown sign-in">
                    <div class="col-sm-12">
                        <a href="${web_url_for('auth_register')}" class="btn btn-success btn-top-signup m-r-xs">Sign Up</a>
                        <a href="${login_url}" class="btn btn-info btn-top-login p-sm">Sign In</a>
                    </div>
                </li>
                %endif
            % endif

        </ul>
    </div>
</div>


</nav>
</div>
</%block>
