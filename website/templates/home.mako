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

<div id="treeGrid">
    <div class="spinner-loading-wrapper">
        <div class="logo-spin logo-lg"></div>
        <p class="m-t-sm fg-load-message"> Loading files...  </p>
    </div>
</div>

</%def>

<%def name="stylesheets()">
  <link rel="stylesheet" href="/static/css/pages/home-page.css">
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
    
    <script src=${"/static/public/js/homeFiles-page.js" | webpack_asset}></script>

</%def>
