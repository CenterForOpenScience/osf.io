<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <h2> Placeholder </h2>
    <h3> Recent Activity </h3>
    <p class="text-muted">Latest activities on your projects adjustable by date and category <p>
    <div id="recentActivityWidget">
        <div class="spinner-loading-wrapper">
            <div class="logo-spin logo-xl"></div>
            <p class="m-t-sm fg-load-message">
                Loading Recent Activity...
            </p>
        </div>
    </div>
</%def>

<%def name="stylesheets()">
  <link rel="stylesheet" href="//code.jquery.com/ui/1.11.4/themes/smoothness/jquery-ui.css">
  <link rel="stylesheet" href="/static/vendor/bower_components/jQuery-ui-Slider-Pips/dist/jquery-ui-slider-pips.css">
  <link rel="stylesheet" href="/static/css/recent-activity-widget.css">
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${"/static/public/js/home.js" | webpack_asset}"></script>
</%def>
