<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <h1>Placeholder</h1>
    <div id="recentActivityWidget"></div>
</%def>
<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
      window.contextVars = $.extend(true, {}, window.contextVars, {})
    </script>
    <script src="${"/static/public/js/home.js" | webpack_asset}"></script>
</%def>
