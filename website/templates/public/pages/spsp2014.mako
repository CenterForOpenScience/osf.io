<%inherit file="base.mako"/>
<%def name="title()">SPSP 2014</%def>
<%def name="content()">

<h2 style="padding-bottom: 30px;">SPSP 2014 Posters & Talks</h2>

<div><a href="http://cos.io/spsp/">Add your poster or talk</a></div>
<div style="padding-bottom: 30px;">Search results by title or author: <input id="gridSearch" /></div>
<div id="grid" style="width: 100%;"></div>

<script type="text/javascript" src="/static/js/spsp.js"></script>
<script type="text/javascript">
    var data = ${data}
    new Meeting.Meeting(data);
</script>

</%def>

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/css/hgrid-base.css" type="text/css" />
</%def>

<%def name="javascript()">
<script src="/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js"></script>
<script src="/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js"></script>
<script src="/static/js/slickgrid.custom.min.js"></script>
</%def>
