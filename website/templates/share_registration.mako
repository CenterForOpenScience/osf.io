<%inherit file="base.mako"/>
<%def name="title()">SHARE</%def>
<%def name="content()">
    <div id="share_registration_iframe"></div>
</%def>

<%def name="javascript_bottom()">
    <script>
        // Mako variables accessible globally
        window.contextVars = $.extend(true, {}, window.contextVars, {
            share: {
                urls: {
                    register: ${ register | sjson, n }
                }
            }
        });
    </script>
    <script src=${"/static/public/js/share-embed-page.js" | webpack_asset}></script>
</%def>
