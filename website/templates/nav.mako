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
      <a class="navbar-brand" href="#">Open Science Framework</a>
    </div>
    <div id="navbar" class="navbar-collapse collapse navbar-right">
      <ul class="nav navbar-nav">
        <li><a href="/explore/activity/">Browse New Projects</a></li>
        <li class="dropdown">
          <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-expanded="false">Explore <span class="caret hidden-xs"></span></a>
          <ul class="dropdown-menu" role="menu">
              <li><a href="/search/?q=*&amp;filter=registration">Registry</a></li>
              <li><a href="/meetings/">Meetings</a></li>
          </ul>
        </li>
        <li class="dropdown">
          <a href="#" class="dropdown-toggle" data-toggle="dropdown" role="button" aria-expanded="false">Help <span class="caret hidden-xs"></span></a>
          <ul class="dropdown-menu" role="menu">
              <li><a href="/4znZP/wiki/home">About</a></li>
              <li><a href="/faq/">FAQ</a></li>
              <li><a href="/getting-started">Getting Started</a></li>
              <li><a href="mailto:support@osf.io" rel="nofollow">Email Support</a></li>
              <li><a href="mailto:contact@osf.io" rel="nofollow">Contact</a></li>
          </ul>
        </li>
        <li class="dropdown sign-in">
          <div class="btn-group">
            <button type="button" class="btn btn-info btn-top-login dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
              Sign in <span class="caret hidden-xs"></span>
            </button>
            <ul class="dropdown-menu" id="menuLogin" role="menu">
              <form class="form" id="formLogin">
                  <div class="form-group"><input name="username" id="username" class="form-control" type="text" placeholder="Username"></div>
                  <div class="form-group"><input name="password" id="password" class="form-control" type="password" placeholder="Password"></div>
                  <div class="form-group"><button type="button" id="btnLogin" class="btn btn-block btn-primary">Login</button></div>
                 <a href="#">Forgot Password?</a>
               </form>
            </ul>
          </div>
        </li>
    </div><!--/.navbar-collapse -->
    </div>


</nav>
    <!-- ko ifnot: onSearchPage -->
        <%include file='./search_bar.mako' />
    <!-- /ko -->
</div>
