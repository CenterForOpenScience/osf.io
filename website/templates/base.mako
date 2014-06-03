<% import json %>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Open Science Framework | ${self.title()}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="${self.description()}">

    ${includes_top()}
    ${self.stylesheets()}
    ${self.javascript()}

    <link href='//fonts.googleapis.com/css?family=Carrois+Gothic|Inika|Patua+One' rel='stylesheet' type='text/css'>

</head>
<body data-spy="scroll" data-target=".nav-list-spy">
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

    <%include file="nav.mako"/>
     ## TODO: shouldn't always have the watermark class
    <div class="watermarked">
        <div class="container">
            % if status:
                <%include file="alert.mako"/>
            % endif
            ${self.content()}
        </div><!-- end container -->
    </div><!-- end watermarked -->

    <%include file="footer.mako"/>

        %if use_cdn:
##            <div id="fb-root"></div>
##            <script>(function(d, s, id) {
##              var js, fjs = d.getElementsByTagName(s)[0];
##              if (d.getElementById(id)) {return;}
##              js = d.createElement(s); js.id = id;
##              js.src = "//connect.facebook.net/en_US/all.js#xfbml=1";
##              fjs.parentNode.insertBefore(js, fjs);
##            }(document, 'script', 'facebook-jssdk'));</script>

            <script>
            var _prum = [['id', '526076f6abe53d9e35000000'],
                         ['mark', 'firstbyte', (new Date()).getTime()]];
            (function() {
                var s = document.getElementsByTagName('script')[0]
                  , p = document.createElement('script');
                p.async = 'async';
                p.src = '//rum-static.pingdom.net/prum.min.js';
                s.parentNode.insertBefore(p, s);
            })();
            </script>

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

        % if piwik_host:
            <script src="${ piwik_host }piwik.js" type="text/javascript"></script>
            <% is_public = node.get('is_public', 'ERROR') if node else True %>
            <script type="text/javascript">

                $(function() {
                    var cvars = [];
                    % if user_id:
                        cvars.push([1, "User ID", "${ user_id }", "visit"])
                        cvars.push([2, "User Name", "${ user_full_name }", "visit"])
                    % endif
                    % if node:
                        <% parent_project = parent_node.get('id') or node.get('id') %>
                        cvars.push([2, "Project ID", "${ parent_project }", "page"]);
                        cvars.push([3, "Node ID", "${ node.get('id') }", "page"]);
                        cvars.push([4, "Tags", ${ json.dumps(','.join(node.get('tags', []))) }, "page"]);
                    % endif
                    // Note: Use cookies for global site ID; only one cookie
                    // will be used, so this won't overflow uwsgi header
                    // buffer.
                    $.osf.trackPiwik("${ piwik_host }", ${ piwik_site_id }, cvars, true);
                });
            </script>
        % endif
        % for url in js_bottom:
        <script src="${url}"></script>
        % endfor
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

<%def name="stylesheets()">
    ### Extra css for this page. ###
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


<%def name="includes_top()">

    <!-- Le HTML5 shim, for IE6-8 support of HTML elements -->
    <!--[if lt IE 9]>
      <script src="//html5shim.googlecode.com/svn/trunk/html5.js"></script>
    <![endif]-->

    <!-- Le styles -->
    ## Don't bundle Bootstrap or else Glyphicons won't work
    <link rel="stylesheet" href="/static/vendor/bower_components/bootstrap/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="/static/vendor/font-awesome/css/font-awesome.min.css">

    % for url in css_all:
    <link rel="stylesheet" href="${url}">
    % endfor

    <script src="//ajax.aspnetcdn.com/ajax/jquery/jquery-2.1.0.min.js"></script>
    <script>window.jQuery || document.write('<script src="/static/vendor/bower_components/jQuery/dist/jquery.min.js">\x3C/script>')</script>
    <script src="//code.jquery.com/ui/1.10.3/jquery-ui.min.js"></script>
    <script>window.jQuery.ui || document.write('<script src="/static/vendor/bower_components/jquery-ui/ui/minified/jquery-ui.min.js">\x3C/script>')</script>
    <script>window.ko || document.write('<script src="/static/vendor/knockout/knockout-3.0.0.min.js">\x3C/script>')</script>
    <script src="/static/vendor/knockout-mapping/knockout.mapping.js"></script>
    <script src="/static/vendor/knockout-punches/knockout.punches.min.js"></script>
    <script src="/static/vendor/knockout-validation/knockout.validation.min.js"></script>

    % for url in js_all:
    <script src="${url}"></script>
    % endfor

    <script>
        // Enable knockout punches
        ko.punches.enableAll();
        // Filebrowser dependencies
        $script(['/static/vendor/bower_components/zeroclipboard/ZeroClipboard.min.js'],
            'zeroclipboard');
        $script(['/static/vendor/dropzone/dropzone.js'], 'dropzone');
        $script(['/static/vendor/bower_components/hgrid/dist/hgrid.js'], 'hgrid');
        $script(['/static/js/dropzone-patch.js']); // exports 'dropzone-patch'
        $script(['/static/js/rubeus.js']); // exports 'rubeus'
        $script(['/static/js/folderPicker.js']);  // exports 'folderPicker'
    </script>

</%def>
