<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
  <div id="shareSearch"></div>
</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>
</%def>
