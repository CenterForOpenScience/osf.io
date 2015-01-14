<div class="osf-nav-wrapper">
<nav class="navbar osf-navbar navbar-fixed-top" role="navigation">
    <div class="container">
        <div class="navbar-header">
            <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
                <span class="sr-only">Toggle navigation</span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
            </button>
            <a class="navbar-brand visible-lg" href="/"><img src="/static/img/cos-white2.png" class="osf-navbar-logo" width="27" alt="COS logo"/> Open Science Framework <span class="brand-version"> BETA</span></a>
            <a class="navbar-brand hidden-lg hidden-xs" href="/"><img src="/static/img/cos-white2.png" class="osf-navbar-logo" width="27" alt="COS logo"/> OSF</a>
            <a class="navbar-brand visible-xs" href="/"><img src="/static/img/cos-white2.png" class="osf-navbar-logo" width="27" alt="COS logo"/> Open Science Framework</a>

        </div><!-- end navbar-header -->
        <div class="collapse navbar-collapse navbar-ex1-collapse">
            <ul class="nav navbar-nav navbar-mid">
                <li class="visible-xs"><a href="/">Home</a></li>
                % if user_name:
                <li><a href="${web_url_for('dashboard')}">My Dashboard</a></li>
                % endif
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
            <ul class="nav navbar-nav navbar-right">
                <li data-bind="click : toggleSearch, css: searchCSS">
                    <a class="" >
                        <span rel="tooltip" title="Search OSF" class="icon-search icon-lg" ></span>
                    </a>
                </li>

                % if user_name and display_name:
                <li>
                    <a class="hidden-lg hidden-xs" href="/profile/">
                        <span rel="tooltip" title="${user_name}" class="osf-gravatar"><img src="${user_gravatar}" alt="User gravatar"/> </span>
                    </a>
                    <a class="visible-lg visible-xs" href="/profile/">
                        <span rel="tooltip" title="${user_name}"><span class="osf-gravatar"> <img src="${user_gravatar}" alt="User gravatar"/> </span> ${display_name}</span>
                    </a>
                </li>
                <li>
                    <a href="${web_url_for('user_profile')}">
                        <span rel="tooltip" title="Settings" class="icon-cog hidden-xs icon-lg"></span>
                        <span class="visible-xs">Settings</span>
                    </a>
                </li>
                <li>
                    <a href="${web_url_for('auth_logout')}">
                        <span rel="tooltip" title="Log&nbsp;out" class="icon-signout hidden-xs icon-lg"></span>
                        <span class="visible-xs">Log out</span>
                    </a>
                </li>
                % elif allow_login:
                <a class="btn btn-primary navbar-btn" href="${web_url_for('auth_login')}">Create an Account or Sign-In</a>
                % endif
            </ul><!-- end nav navbar-nav navbar-right -->
        </div><!-- end navbar-collapse -->
    </div><!-- end container-->
</nav>

<div class="osf-search" data-bind="visible: showSearch">
    <div class="container">
        <div class="row">
            <div class="col-md-12">
                <form class="input-group" data-bind="submit: submit">
                    <input name="searchBar" type="text" class="osf-search-input form-control" placeholder="Search" >
                    <span class="input-group-btn">
                        
                        <span type=button class="btn osf-search-btn" data-bind="click: submit"><i class="icon-circle-arrow-right icon-lg"></i></span>
                        <span type=button class="btn osf-search-btn" data-bind="click: help"><i class="icon-question icon-lg"></i></span>
                    </span>
                </form>
            </div>
        </div>  
    </div>     
</div>
</div>

