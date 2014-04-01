<%inherit file="base.mako"/>
<%def name="title()">ASB 2014</%def>

<%def name="content()">
    <h2 style="padding-bottom: 30px;">ASB 2014 Posters & Talks</h2>
    <div><a href="http://www.sebiologists.org/meetings/talks_posters.html">Add your poster or talk</a></div>
    <div style="padding-bottom: 30px;">Search results by title or author: <input id="gridSearch" /></div>
    <div id="grid" style="width: 100%;"></div>
</%def>

<%def name="javascript_bottom()">
    <script type="text/javascript" src="/static/js/conference.js"></script>
    <script type="text/javascript">
        var data = ${data}
        new Meeting.Meeting(data);
    </script>
</%def>
