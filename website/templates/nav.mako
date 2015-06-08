<div class="osf-nav-wrapper">
<nav class="navbar osf-navbar navbar-fixed-top" id="navbarScope" role="navigation">
    <div class="container">
        <div class="navbar-header">
            <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
                <span class="sr-only">Toggle navigation</span>
                <span class="fa fa-bars fa-lg fa-inverse"></span>
            </button>
            <!-- ko ifnot: onSearchPage -->
            <span class="visible-xs" data-bind="click : toggleSearch, css: searchCSS">
                <a class="osf-xs-search pull-right" >
                  <span rel="tooltip" data-placement="bottom" title="Search OSF" class="fa fa-search fa-lg fa-inverse" ></span>
                </a>
            </span>
            <!-- /ko -->
            <a class="navbar-brand visible-lg" href="/"><img src="/static/img/cos-white2.png" class="osf-navbar-logo" width="27" alt="COS logo"/> Open Science Framework <span class="brand-version"> BETA</span></a>
            <a class="navbar-brand hidden-lg" href="/"><img src="/static/img/cos-white2.png" class="osf-navbar-logo" width="27" alt="COS logo"/> OSF</a>

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
                        <li><a href="/search/?q=*&filter=registration">Registry</a></li>
                        <li><a href="/meetings/">Meetings</a></li>
                        <li><a href="/explore/activity/">Public Activity</a></li>
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
                <!-- ko ifnot: onSearchPage -->
                <li class="hidden-xs" data-bind="click : toggleSearch, css: searchCSS">
                    <a class="" >
                        <span rel="tooltip" data-placement="bottom" title="Search OSF" class="fa fa-search fa-lg" ></span>
                    </a>
                </li>
                <!-- /ko -->
                % if user_name and display_name:
                <li>
                    <a class="hidden-lg hidden-xs" href="/profile/">
                        <span rel="tooltip" data-placement="bottom" title="${user_name}" class="osf-gravatar"><img src="${user_gravatar}" alt="User gravatar"/> </span>
                    </a>
                    <a class="visible-lg visible-xs" href="/profile/">
                        <span rel="tooltip" data-placement="bottom" title="${user_name}"><span class="osf-gravatar"> <img src="${user_gravatar}" alt="User gravatar"/> </span> ${display_name}</span>
                    </a>
                </li>
                <li>
                    <a href="${web_url_for('user_profile')}">
                        <span rel="tooltip" data-placement="bottom" title="Settings" class="fa fa-cog hidden-xs fa-lg"></span>
                        <span class="visible-xs">Settings</span>
                    </a>
                </li>
                <li>
                    <a href="${web_url_for('auth_logout')}">
                        <span rel="tooltip" data-placement="bottom" title="Log&nbsp;out" class="fa fa-sign-out hidden-xs fa-lg"></span>
                        <span class="visible-xs">Log out</span>
                    </a>
                </li>
                % elif allow_login:
                <li data-bind="with: $root.signIn">
                    <form
                            id="signInForm"
                            class="navbar-form navbar-right"
                            data-bind="submit: submit"
                            action="${login_url}"
                            method="POST"
                        >
                        <div class="form-group">
                            <input type="email" class="input-sm form-control" data-bind="value: username" name="username" placeholder="Email" aria-label="Username">
                        </div>
                        <div class="form-group">
                            <input type="password" class="input input-sm form-control" data-bind="value: password" name="password" placeholder="Password" aria-label="Password">
                        </div>
                        <button type="submit" class="btn btn-sm btn-success">Sign In</button>
                    </form>
                </li>
                <li>
                    <a href="${web_url_for('forgot_password_get')}">Forgot Password?</a>
                </li>
                % endif
            </ul><!-- end nav navbar-nav navbar-right -->
        </div><!-- end navbar-collapse -->
    </div><!-- end container-->
</nav>
    <!-- ko ifnot: onSearchPage -->
        <%include file='./search_bar.mako' />
    <!-- /ko -->
</div>
