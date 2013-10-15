<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Open Science Framework</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="">
    <meta name="author" content="">

    <!-- Le HTML5 shim, for IE6-8 support of HTML elements -->
    <!--[if lt IE 9]>
      <script src="//html5shim.googlecode.com/svn/trunk/html5.js"></script>
    <![endif]-->

    <!-- Le styles -->
    %if use_cdn:
        <link rel="stylesheet" type="text/css" href="//ajax.googleapis.com/ajax/libs/jqueryui/1/themes/flick/jquery-ui.css">
    %else:
        <link rel="stylesheet" type="text/css" href="/static/jquery-ui.css">
    %endif
    <link rel="stylesheet" type="text/css" href="/static/jquery.tagit.css">
    <link href="/static/tagit.ui-zendesk.css" rel="stylesheet" type="stylesheet">
    <link rel="stylesheet" type="text/css" href="/static/pagedown/demo.css" />
    <link href="/static/vendor/bootstrap3/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/vendor/bootstrap3-editable/css/bootstrap-editable.css">
    <link rel="stylesheet" href="/static/vendor/font-awesome/css/font-awesome.min.css">
    <link href="/static/jquery-treeview/jquery.treeview.css" rel="stylesheet" type="text/css" media="screen" />
    <link href="/static/site.css" rel="stylesheet">
    <!-- Le Javascript -->
    %if use_cdn:
        <script src="//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
        <script src="//cdnjs.cloudflare.com/ajax/libs/underscore.js/1.3.3/underscore-min.js"></script>
        <script src="//cdnjs.cloudflare.com/ajax/libs/handlebars.js/1.0.0.beta2/handlebars.min.js"></script>

        <script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.8.12/jquery-ui.min.js" type="text/javascript" charset="utf-8"></script>
        <script src="//cdnjs.cloudflare.com/ajax/libs/ember.js/0.9.5/ember-0.9.5.min.js"></script>
    %else:
        <script src="/static/vendor/jquery/jquery-1.10.2.min.js"></script>
        <script src="/static/vendor/jquery/jquery-migrate-1.2.1.min.js"></script>
        <script src="/static/underscore-min.js"></script>
        <script src="/static/handlebars.min.js"></script>
        <script src="/static/jquery-ui.min.js" type="text/javascript" charset="utf-8"></script>
        <script src="/static/ember-0.9.5.min.js"></script>
    %endif
    <script src="/static/vendor/bootstrap3/js/bootstrap.min.js"></script>
    <script src="/static/tag-it.js"></script>
    <script src="/static/jquery.autoresize.js"></script>
    <script src="//cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.0.0/bootbox.min.js"></script>
    <script src="/static/vendor/bootstrap3-editable/js/bootstrap-editable.min.js"></script>
    <script src="/static/jquery-treeview/jquery.treeview.js" type="text/javascript"></script>
    <script src="/static/ember-formbuilder.js"></script>
    <script src="/static/site.js"></script>

    <!--uploads-->
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/jquery.fileupload-ui.css">
    <link rel="stylesheet" href="/static/pygments.css" />
</head>
<body>
    % if dev_mode:
    <style>
        #devmode {
            position:fixed;
            bottom:0;
            left:0;
            border-top-right-radius:8px;
            background-color:red;
            color:white;
            padding:.5em;
        }
    </style>
    <div id='devmode'><strong>WARNING</strong>: This site is running in development mode.</div>
    % endif
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
    <div class="watermarked">
    <div role="content" class="content container">
    % if status:
        <div id="alert-container">
        % for s in status:
            <div class='alert alert-block alert-warning fade in'><a class='close' data-dismiss='alert' href='#'>&times;</a><p>${s}</p></div>
        % endfor
        </div>
    % endif

