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
                <span class="hidden-xs"> ${osf_page_name} </span>
              % if nav_dropdown:
                <span class="current-service"><strong>${service_name}</strong></span>
              % endif
            </a>
        </div>
        % if nav_dropdown:
        <div class="dropdown primary-nav">
            <button data-bind="click: trackClick.bind($data, 'Dropdown Arrow')" id="primary-navigation" class="dropdown-toggle btn-link" data-toggle="dropdown" role="button" aria-expanded="false" aria-label="Toggle primary navigation">
                <span class="fa fa-caret-down fa-2x"></span>
            </button>
            <ul class="dropdown-menu service-dropdown" role="menu">
                <li><a data-bind="click: trackClick.bind($data, 'Home')" href="${domain}">${osf_page_name}<b>HOME</b></a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Preprints')" href="${domain}preprints/">${osf_page_name}<b>PREPRINTS</b></a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Registries')" href="${domain}registries/">${osf_page_name}<b>REGISTRIES</b></a></li>
                <li><a data-bind="click: trackClick.bind($data, 'Meetings')" href="${domain}meetings/">${osf_page_name}<b>MEETINGS</b></a></li>
            </ul>
        </div>
        % endif
    </div>
    <div id="navbar" class="navbar-collapse collapse navbar-right">
        <ul class="nav navbar-nav"></ul>
    </div><!--/.navbar-collapse -->

    <div class="navbar-collapse collapse navbar-right" id="secondary-navigation">
        <ul class="nav navbar-nav">
            % if service_name == 'HOME':
                % if user_name:
<!--
                    <li><a data-bind="click: trackClick.bind($data, 'MyQuickFiles')" href="${domain}quickfiles/">My Quick Files</a></li>
-->
                    <li><a data-bind="click: trackClick.bind($data, 'MyProjects')" href="${domain}myprojects/">My Projects</a></li>
                % endif
                    <li><a id="navbar-search" data-bind="click: trackClick.bind($data, 'Search')" href="${domain}search/">Search</a></li>
            % endif
            % if nav_support:
            <li class="dropdown">
            <a id="navbar-support" data-bind="click: trackClick.bind($data, '${service_name} Support')" href="${service_support_url}">Support</a>
            </li>
            <li class="navbar-donate-button"><a id="navbar-donate" data-bind="click: trackClick.bind($data, 'Donate')" href="https://cos.io/donate">Donate</a></li>
            % endif:
            % if user_name and display_name:
            <li class="dropdown">
                <a class="dropdown-toggle btn-link" data-toggle="dropdown" role="button" aria-expanded="false" aria-label="Toggle auth dropdown">
                    <div class="osf-profile-image">
                        <img src="${user_profile_image}" alt="User profile image">
                    </div>
                    <div class="nav-profile-name">
                            ${display_name}
                    </div>
                    <div class="caret"></div>
                </a>

                <ul class="dropdown-menu auth-dropdown" role="menu">
                    <li><a data-bind="click: trackClick.bind($data, 'MyProfile')" href="${domain}profile/"><i class="fa fa-user fa-lg p-r-xs"></i> My Profile</a></li>
                    % if nav_support:
                    <li><a data-bind="click: trackClick.bind($data, 'Support')" href="${domain}support/" ><i class="fa fa-life-ring fa-lg p-r-xs"></i> OSF Support</a></li>
                    % endif
                    <li><a data-bind="click: trackClick.bind($data, 'Settings')" href="${web_url_for('user_profile')}"><i class="fa fa-cog fa-lg p-r-xs"></i> Settings</a></li>
                    <li><a data-bind="click: trackClick.bind($data, 'Logout')" href="${web_url_for('auth_logout')}"><i class="fa fa-sign-out fa-lg p-r-xs"></i> Log out</a></li>
                </ul>
            </li>
            % elif allow_login:
                %if institution:
                    <li class="dropdown sign-in">
                    <div class="btn-group">
                        <a href="${domain}login/?campaign=institution&next=${redirect_url}">
                            <button type="button" class="btn btn-info btn-top-login">
                            Sign in <span class="hidden-xs"><i class="fa fa-arrow-right"></i></span>
                            </button>
                        </a>
                    </div>
                    </li>
                %else :
		%if not embedded_ds:
                <li class="dropdown sign-in">
                    <div class="col-sm-12">
<!--
                        <a data-bind="click: trackClick.bind($data, 'SignUp')" href="${web_url_for('auth_register')}" class="btn btn-success btn-top-signup m-r-xs">Sign Up</a>
-->
                        <a data-bind="click: trackClick.bind($data, 'SignIn')" href="${login_url}" class="btn btn-info btn-top-login p-sm">Sign In</a>
                    </div>
                </li>
		%else :
<!-- embedded DS -->
<script type="text/javascript" charset="UTF-8"><!--
  var li = document.createElement('li');
  li.innerHTML = '<a id="shibbolethDS" href="#" class="user-item login-link" onclick="return toggleDs()">DS</a>';
  document.getElementById('login-link').parentNode.parentNode.appendChild(li);
    //-->
</script>
<script type="text/javascript" src="/js/embedded-wayf_disp.js"></script>
<div id="wayfInMenu" style="float: right; clear: right; position: relative;">
<script type="text/javascript" src="/js/embedded-wayf_config.js"></script>
<script type="text/javascript" charset="UTF-8"><!--
  document.write('<script type="text/javascript" src="https://test-ds.gakunin.nii.ac.jp/WAYF/embedded-wayf.js?' + (new Date().getTime()) + '"></scr'+'ipt>');
    //-->
</script>
<!-- embbeded DS -->
</div>
                %endif
                %endif
            % endif

        </ul>
    </div>
</div>
</nav>
    <div class="container-fluid">
        <div class="row">
            <div class="col">
                ## Maintenance alert
                % if maintenance:
                    <div id="maintenance" class="scripted alert alert-dismissible" role="alert">
                    <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                        <span aria-hidden="true">&times;</span></button>
                    <strong>Notice:</strong>
                    % if maintenance['message']:
                        ${maintenance['message']}
                    % else:
                        The site will undergo maintenance between <span id="maintenanceTime"></span>.
                        Thank you for your patience.
                    % endif
                </div>
                % endif
                ## End Maintenance alert
            </div>
        </div>
    </div>
</div>
</%def>
