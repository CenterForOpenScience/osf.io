<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
  <div id="shareSearch"></div>
</%def>

<%def name="javascript_bottom()">
    <link href="/static/vendor/bower_components/c3/c3.css" rel="stylesheet" type="text/css">
    <link href="/static/css/share-search.css" rel="stylesheet" type="text/css">
    <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>
</%def>
