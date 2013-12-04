<%inherit file="base.mako"/>
<%def name="content()">

<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div>
    <div class="col-md-9 wiki">
        ${wiki_content}
    </div>

    <div class="col-md-3">
        <div mod-meta='{
                "tpl": "project/wiki/nav.mako",
                "replace": true
            }'></div>
        <div mod-meta='{
                "tpl": "project/wiki/history.mako",
                "replace": true
            }'></div>
    </div>


</div>
</%def>
