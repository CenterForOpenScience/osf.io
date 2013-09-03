<%
    import framework, website.settings
    username = framework.get_current_username()
    if username:
        if len(username) > 22:
            display_name = '%s...%s' % (username[:9],username[-10:])
        else:
            display_name = username
%>
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
      <script src="http://html5shim.googlecode.com/svn/trunk/html5.js"></script>
    <![endif]-->

    <!-- Le styles -->
    %if website.settings.use_cdn_for_client_libs:
        <link rel="stylesheet" type="text/css" href="http://ajax.googleapis.com/ajax/libs/jqueryui/1/themes/flick/jquery-ui.css">
    %else:
        <link rel="stylesheet" type="text/css" href="/static/jquery-ui.css">
    %endif 
    <link rel="stylesheet" type="text/css" href="/static/jquery.tagit.css">
    <link href="/static/tagit.ui-zendesk.css" rel="stylesheet" type="stylesheet">
    <link rel="stylesheet" type="text/css" href="/static/pagedown/demo.css" />
    <link href="/static/bootstrap/css/bootstrap.css" rel="stylesheet">
    <link href="/static/jquery-treeview/jquery.treeview.css" rel="stylesheet" type="text/css" media="screen" />
    <link href="/static/site.css" rel="stylesheet">
    <style type="text/css">
      body {
        padding-top: 60px;
      }
      
      .editing .display,
      .edit {
      	display: none;
      }
      .editing .edit {
      	display: block;
      }
    </style>
    
    %if website.settings.use_cdn_for_client_libs:
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js"></script>
        <script src="http://cdnjs.cloudflare.com/ajax/libs/underscore.js/1.3.3/underscore-min.js"></script>
        <script src="http://cdnjs.cloudflare.com/ajax/libs/backbone.js/0.9.2/backbone-min.js"></script>
        <script src="http://cdnjs.cloudflare.com/ajax/libs/handlebars.js/1.0.0.beta2/handlebars.min.js"></script>
        
        <script src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.12/jquery-ui.min.js" type="text/javascript" charset="utf-8"></script>
        <script src="/static/bootstrap/js/bootstrap.min.js"></script>
        <script src="/static/tag-it.js"></script>
        <script src="/static/jquery.autoresize.js"></script>
        <script src="/static/bootstrap-editable/js/bootstrap-editable.min.js"></script>
        <script src="/static/jquery-treeview/jquery.treeview.js" type="text/javascript"></script>
        <script src="http://cloud.github.com/downloads/emberjs/ember.js/ember-0.9.5.min.js"></script>
        <script src="/static/ember-formbuilder.js"></script>
        <script src="/static/site.js"></script>
    %else:
        <script src="/static/jquery.min.js"></script>
        <script src="/static/underscore-min.js"></script>
        <script src="/static/backbone-min.js"></script>
        <script src="/static/handlebars.min.js"></script>
        
        <script src="/static/jquery-ui.min.js" type="text/javascript" charset="utf-8"></script>
        <script src="/static/bootstrap/js/bootstrap.min.js"></script>
        <script src="/static/tag-it.js"></script>
        <script src="/static/jquery.autoresize.js"></script>
        <script src="/static/bootstrap-editable/js/bootstrap-editable.min.js"></script>
        <script src="/static/jquery-treeview/jquery.treeview.js" type="text/javascript"></script>
        <script src="/static/ember-0.9.5.min.js"></script>
        <script src="/static/ember-formbuilder.js"></script>
        <script src="/static/site.js"></script>
    %endif 

    
    <script>
    var openCloseNode = function(node_id){
  icon = $("#icon-" + node_id);
  body = $("#body-" + node_id);
  
  body.toggleClass('hide');
  
  if ( body.hasClass('hide') ) {
    icon.removeClass('icon-minus');
    icon.addClass('icon-plus');
  }else{
    icon.removeClass('icon-plus');
    icon.addClass('icon-minus');
  }
};
</script>
    <!--uploads-->
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/jquery.fileupload-ui.css">
    <link rel="stylesheet" href="/static/pygments.css" />
    <link href="/static/bootstrap-editable/css/bootstrap-editable.css" rel="stylesheet">
    <%include file='_modal_confirm.mako' />
</head>
<body>
    % if website.settings.dev_mode:
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
    <div class="navbar navbar-fixed-top">
        <div class="navbar-inner">
            <div class="container">
                <a class="brand" style="padding-left: 10px; padding-right: 10px;" href="/">Open Science Framework<span style="font-size: 8px;"> BETA</span></a>
                <ul class="nav">
                    %if username:
                    <li><a rel="tooltip" title="My Dashboard" href="/dashboard">Dashboard</a></li>
                    %endif
                    <li class='dropdown'>
                        <a href="#" class='dropdown-toggle' data-toggle='dropdown'>
                            Explore
                            <b class='caret'></b>
                        </a>
                        <ul class="dropdown-menu">
                            <li><a href="/explore">Collaborator Network</a></li>
                            <li><a href="/explore/activity">Public Activity</a></li>
                        </ul>
                    </li>
                    <li class='dropdown'>
                        <a href="#" class='dropdown-toggle' data-toggle='dropdown'>
                            Help<b class='caret'></b>
                        </a>
                        <ul class='dropdown-menu'>
                            <li><a href="/project/4znZP/wiki/home">About</a></li>
                            <li><a href="/faq">FAQ</a></li>
                            <li><a href="/getting-started">Getting Started</a></li>
                        </ul>
                    </li>


                </ul>
                <form class="navbar-search pull-left" action="/search/" method="get">
                    <input type="text" class="search-query" placeholder="Search" name="q">
                </form>
                <ul class="nav pull-right" id='navbar-icons'>
                    %if username and display_name:
                    <li><a href="/profile">${display_name}</a></li>
                    <li><a rel="tooltip" title="Settings" href="/settings"><span class='icon-white icon-cog'>&nbsp;</span></a></li>
                    <li><a rel='tooltip' title='Log out' href='/logout'><span class="icon-white icon-off">&nbsp;</span></a></li>
                    %else:
                        %if website.settings.allow_login:
                        <li><a class="btn btn-primary" href="/account" style="background-color:rgb(0, 85, 204);;color:white;padding:5px 9px;font-size: 11px; line-height: 16px;">Create an Account or Sign-In</a></li>
                        %else:
                        %endif
                    %endif
                </ul>
            </div>
        </div>
    </div>
    <div class="watermarked">
    <div class="container">
        %if status:
            <div id="alert-container">
            %for s in status:
                <div class='alert alert-block alert-warning fade in'><a class='close' data-dismiss='alert' href='#'>&times;</a><p>${s}</p></div>
            %endfor
            </div>
        %endif