<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
    <div style="height: 100%; padding-top: 25px;">
        ## <iframe class="registration_form" src="http://localhost:8000/provider_registration/pre_register/" style="border: 0; width: 100%; height: 1700px; display:block;"></iframe>
        <iframe class="registration_form" src="http://localhost:8000/provider_registration/" style="border: 0; width: 100%;"></iframe>
    </div>
</%def>

<%def name="javascript_bottom()">
    ## <script src=${"/static/public/js/share-search-page.js" | webpack_asset}></script>
    <script type="text/javascript" language="javascript"> 
        $('.registration_form').css('height', $(window).height()+'px');
    </script>
</%def>z
