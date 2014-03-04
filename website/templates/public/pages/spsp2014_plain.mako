<html>

<head>

    <title>SPSP Presentations 2014</title>

    <link rel="stylesheet" href="/static/vendor/bootstrap3/css/bootstrap-custom.css">
    <link rel="stylesheet" href="/static/vendor/font-awesome/css/font-awesome.min.css">
    % for url in css_all:
    <link rel="stylesheet" href="${url}">
    % endfor

    <script src="//ajax.aspnetcdn.com/ajax/jquery/jquery-2.1.0.min.js"></script>
    <script>window.jQuery || document.write('<script src="/static/vendor/bower_components/jQuery/dist/jquery.min.js">\x3C/script>')</script>
    <script src="//code.jquery.com/ui/1.10.3/jquery-ui.min.js"></script>
    <script>window.jQuery.ui || document.write('<script src="/static/vendor/bower_components/jquery-ui/ui/minified/jquery-ui.min.js">\x3C/script>')</script>
    % for url in js_all + js_bottom:
        <script src="${url}"></script>
    % endfor

</head>

<body>

    <div class="container">

        <h2 style="padding-bottom: 30px;">SPSP 2014 Posters & Talks</h2>
        <div><a href="http://cos.io/spsp/">Add your poster or talk</a></div>
        <div style="padding-bottom: 30px;">Search results by title or author: <input id="gridSearch" /></div>
        <div id="grid" style="width: 100%;"></div>

    </div>

    <script type="text/javascript" src="/static/js/spsp.js"></script>
    <script type="text/javascript">
        var data = ${data}
        new Meeting.Meeting(data);
    </script>

</body>

</html>
