<html>

<head>

    <title>SPSP Presentations 2014</title>

    <link rel="stylesheet" href="/static/vendor/bootstrap3/css/bootstrap-custom.css">
    <link rel="stylesheet" href="/static/vendor/font-awesome/css/font-awesome.min.css">

    % for url in css_all:
        <link rel="stylesheet" href="${url}">
    % endfor

    % for url in js_all:
        <script src="${url}"></script>
    % endfor

    <script src="/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js"></script>
    <script src="/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js"></script>
    <script src="/static/vendor/hgrid/hgrid.js"></script>

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
