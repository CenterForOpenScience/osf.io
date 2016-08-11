<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
  <br>
  <div class="alert alert-info" role="alert">
    We are excited to share that we are nearing completion of an update to SHARE's data and related discovery pages. As a result, only minor updates will be applied to version 1 (v1) of SHARE over the next few weeks while v2 is being prepared for release. More to come soon!
  </div>
  <div id="shareSearch"></div>
</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>
</%def>
