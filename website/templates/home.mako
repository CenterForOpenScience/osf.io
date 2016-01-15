<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
     <div>
            <div id="addQuickProjectSearchWrap"></div>
     </div>

    <div>
            <div id="newAndNoteworthyWrap"></div>
    </div>


</%def>



