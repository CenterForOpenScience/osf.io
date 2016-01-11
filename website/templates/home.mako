<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
     <div class="container">
            <div id="addQuickProjectSearchWrap"></div>
     </div>


</%def>



