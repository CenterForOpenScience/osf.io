<%inherit file="base.mako"/>

<%def name="content()">
    <br>
    <div class="container"><div class="col-sm-3"><img class="img-circle" height="110" width="110" src=${ logo_path }></div><h1 class="col-sm-9">${ name }</h1></div>
    <div id="inst">
        <span data-bind="foreach: allNodes">
            <h3><a data-bind="attr: { href: links.html}"><span data-bind="text: attributes.title"></span> </a></h3>
        </span>
    </div>
</%def>

<%def name="javascript_bottom()">

    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
           institution: {
               name: ${ name | sjson, n},
               id: ${ id | sjson, n},
               logoPath: ${ logo_path | sjson, n},
           }
        });
    </script>
    ${parent.javascript_bottom()}
    <script src="${"/static/public/js/institution-page.js" | webpack_asset}"></script>
</%def>

