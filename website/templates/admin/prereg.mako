<%inherit file="../base.mako"/>


<%def name="content()">

</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}

<script src=${"/static/public/js/prereg-admin-page.js" | webpack_asset}></script>
</%def>
