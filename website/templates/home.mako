<%inherit file="base.mako"/>
<%def name="title()">Home</%def>

<%def name="content_wrap()">
    <div class="watermarked">
        <div class="container ${self.container_class()}">
            % if status:
                ${self.alert()}
            % endif
        </div><!-- end container -->
        ${self.content()}
    </div><!-- end watermarked -->
</%def>


<%def name="content()">

    <div id="osfHome"></div>

</%def>

<%def name="stylesheets()">
  <link rel="stylesheet" href="/static/css/pages/home-page.css">
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
</%def>
