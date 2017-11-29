<%def name="nav(service_name, service_url, service_support_url)">
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
        <a class="navbar-brand" href="/" aria-label="Go home"><span class="osf-navbar-logo"></span></a>
        <div class="service-name">
            <a href="${service_url}">
                <span class="hidden-xs"> OSF </span>
                <span class="current-service"><strong>${service_name}</strong></span>
            </a>
        </div>
        <div class="dropdown primary-nav">
            <button data-bind="click: trackClick.bind($data, 'Dropdown Arrow')" id="primary-navigation" class="dropdown-toggle btn-link" data-toggle="dropdown" role="button" aria-expanded="false" aria-label="Toggle primary navigation">
                <span class="fa fa-caret-down fa-2x"></span>
            </button>
            <ul class="dropdown-menu service-dropdown" role="menu">
                <li><a data-bind="click: trackClick.bind($data, 'Home')" href="${domain}">OSF<b>HOME</b></a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Preprints')" href="${domain}preprints/">OSF<b>PREPRINTS</b></a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Registries')" href="${domain}registries/">OSF<b>REGISTRIES</b></a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Meetings')" href="${domain}meetings/">OSF<b>MEETINGS</b></a></li>
            </ul>
        </div>
    </div>
    <div id="navbar" class="navbar-collapse collapse navbar-right">
        <ul class="nav navbar-nav"></ul>
    </div><!--/.navbar-collapse -->

    <div class="navbar-collapse collapse navbar-right" id="secondary-navigation">
        <ul class="nav navbar-nav">
            % if service_name == 'HOME':
                % if user_name:
                    <li><a data-bind="click: trackClick.bind($data, 'MyProjects')" href="${domain}myprojects/">My Projects</a></li>
                % endif
                    <li><a id="navbar-search" data-bind="click: trackClick.bind($data, 'Search')" href="${domain}search/">Search</a></li>
            % endif
            <li class="dropdown">
            <a id="navbar-support" data-bind="click: trackClick.bind($data, '${service_name} Support')" href="${service_support_url}">Support</a>
            </li>
            <li class="navbar-donate-button"><a id="navbar-donate" data-bind="click: trackClick.bind($data, 'Donate')" href="https://cos.io/donate">Donate</a></li>
            % if user_name and display_name:
            <li class="dropdown">
            <button class="dropdown-toggle nav-user-dropdown btn-link" data-toggle="dropdown" role="button" aria-expanded="false" aria-label="Toggle auth dropdown">
                <span class="osf-gravatar">
                    <img src="${user_gravatar}" alt="User gravatar">
                </span> ${display_name}
                <span class="caret"></span>
            </button>

            <ul class="dropdown-menu auth-dropdown" role="menu">
                <li><a data-bind="click: trackClick.bind($data, 'MyProfile')" href="${domain}profile/"><i class="fa fa-user fa-lg p-r-xs"></i> My Profile</a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Support')" href="${domain}support/" ><i class="fa fa-life-ring fa-lg p-r-xs"></i> OSF Support</a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Settings')" href="${web_url_for('user_profile')}"><i class="fa fa-cog fa-lg p-r-xs"></i> Settings</a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Logout')" href="${web_url_for('auth_logout')}"><i class="fa fa-sign-out fa-lg p-r-xs"></i> Log out</a></li>
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
                        <a data-bind="click: trackClick.bind($data, 'SignUp')" href="${web_url_for('auth_register')}" class="btn btn-success btn-top-signup m-r-xs">Sign Up</a>
                        <a data-bind="click: trackClick.bind($data, 'SignIn')" href="${login_url}" class="btn btn-info btn-top-login p-sm">Sign In</a>
                    </div>
                </li>
                %endif
            % endif

        </ul>
    </div>
</div>
</nav>
</div>
</%def>
