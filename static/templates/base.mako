<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Open Science Framework | ${self.title()}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="${self.description()}">

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
    ${self.javascript()}

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

    <div mod-meta='{"tpl": "nav.mako", "replace": true}'></div>
     ## TODO: shouldn't always have the watermark class
    <div class="watermarked">
        <div class="container">
            % if status:
                <div mod-meta='{"tpl": "alert.mako", "replace": true}'></div>
            % endif
            ${self.content()}
        </div><!-- end container -->
    </div><!-- end watermarked -->

    <div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>

        %if use_cdn:
            <div id="fb-root"></div>
            <script>(function(d, s, id) {
              var js, fjs = d.getElementsByTagName(s)[0];
              if (d.getElementById(id)) {return;}
              js = d.createElement(s); js.id = id;
              js.src = "//connect.facebook.net/en_US/all.js#xfbml=1";
              fjs.parentNode.insertBefore(js, fjs);
            }(document, 'script', 'facebook-jssdk'));</script>

            <script type="text/javascript">

              var _gaq = _gaq || [];
              _gaq.push(['_setAccount', 'UA-26813616-1']);
              _gaq.push(['_trackPageview']);

              (function() {
                var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
                ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
                var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
              })();
            </script>
        %endif
        ${self.javascript_bottom()}
    </body>
</html>


###### Base template functions #####

<%def name="title()">
    ### The page title ###
</%def>

<%def name="description()">
    ### The page description ###
</%def>

<%def name="javascript()">
    ### Additional javascript, loaded at the top of the page ###
</%def>

<%def name="content()">
    ### The body content. ###
</%def>

<%def name="javascript_bottom()">
    ### Javascript loaded at the bottom of the page ###
</%def>

