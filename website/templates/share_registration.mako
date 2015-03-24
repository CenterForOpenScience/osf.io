<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
    <div id="share_registration_iframe"></div>
</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/share-embed-page.js" | webpack_asset}></script>
</%def>
