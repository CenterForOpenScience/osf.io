<html>

<head>

    <title>SPSP Presentations 2014</title>

    <%namespace name="globals" file="base.mako" />
    ${globals.includes_top()}}

    % for url in js_bottom:
        <script src="${url}"></script>
    % endfor

</head>

<body>

    <div class="container">

        <h2 style="padding-bottom: 30px;">SPSP 2014 Posters & Talks</h2>
        <div style="padding-bottom: 30px;">Search results by title or author: <input id="gridSearch" /></div>
        <div id="grid" style="width: 100%;"></div>

    </div>

    <script type="text/javascript">
        var data = ${data};
        $script('/static/js/conference.js');
        $script.ready('conference', function() {
            new Meeting(data);
        })
    </script>

</body>

</html>
