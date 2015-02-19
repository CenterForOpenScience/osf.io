<%inherit file="base.mako"/>
<%def name="title()">SHARE STATS</%def>
<%def name="content()">
  <link href="/static/vendor/bower_components/c3/c3.css" rel="stylesheet" type="text/css">
  <div id="shareDashboard1"></div>
  <div id="shareDashboard2"></div>
  <div id="shareDashboard3"></div>

</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-dashboard.js" | webpack_asset}></script>
</%def>
