<%inherit file="base.mako"/>
<%def name="title()">SPSP 2014</%def>

<%def name="content()">
    <h2 style="padding-bottom: 30px;">SPSP 2014 Posters & Talks</h2>
    <div><a href="http://cos.io/spsp/">Add your poster or talk</a></div>
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
