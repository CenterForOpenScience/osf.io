<%inherit file="base.mako"/>
<%def name="title()">Home</%def>

<%def name="content_wrap()">
    <div class="watermarked">
        <div class="home-page-alert">
            % if status:
                ${self.alert()}
            % endif
        </div>
    </div><!-- end watermarked -->

    ${self.content()}
</%def>


<%def name="content()">

    <div id="osfHome"></div>

</%def>

<%def name="stylesheets()">
  <link rel="stylesheet" href="/static/css/pages/home-page.css">
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            'user_institutions': ${ user_institutions or [] | sjson, n },
        });
    </script>
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
</%def>
