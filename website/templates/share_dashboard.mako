<%inherit file="base.mako"/>
<%def name="title()">SHARE STATS</%def>
<%def name="content()">
  <div id="shareDashboard">
    <!-- Load c3.css -->
  <link href="/path/to/c3.css" rel="stylesheet" type="text/css">

  HELLO SOME STUFF

  </div>
</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>
</%def>
