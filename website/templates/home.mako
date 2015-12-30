<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <h1>Placeholder</h1>
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
     <div class="col-xs-4">
            <div id="addQuickProjectSearchWrap" class="m-t-md pull-right"></div>
     </div>


</%def>



