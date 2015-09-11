<html>

<head>

    <title>${ meeting['name'] } Presentations</title>

    <%namespace name="globals" file="base.mako" />
    ${globals.includes_top()}

    % if sentry_dsn_js:
    <script src="/static/vendor/bower_components/raven-js/dist/raven.min.js"></script>
    <script src="/static/vendor/bower_components/raven-js/plugins/jquery.js"></script>
    <script>
        Raven.config('${ sentry_dsn_js }', {}).install();
    </script>
    % else:
    <script>
        window.Raven = {};
        Raven.captureMessage = function(msg, context) {
            console.error('=== Mock Raven.captureMessage called with: ===');
            console.log('Message: ' + msg);
            console.log(context);
        };
        Raven.captureException = function(err, context) {
            console.error('=== Mock Raven.captureException called with: ===');
            console.log('Error: ' + err);
            console.log(context);
        };
    </script>
    % endif

    <script src="${"/static/public/js/vendor.js" | webpack_asset}"></script>

    % for url in globals.javascript_bottom():
        <script src="${url}"></script>
    % endfor

</head>

<body>

    <div class="container">
        <%include file="public/pages/meeting_body.mako" />
    </div>

    <script type="text/javascript">
        window.contextVars = window.contextVars || {};
        window.contextVars.meetingData = ${ data | sjson, n };

        $('#addLink').on('click', function(e) {
            e.preventDefault();
            $('#submit').slideToggle();
        })
    </script>
    <script src=${"/static/public/js/conference-page.js" | webpack_asset}></script>
</body>

</html>
