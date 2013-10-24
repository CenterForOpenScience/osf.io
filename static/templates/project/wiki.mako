<%inherit file="base.mako"/>
<%def name="title()">Wiki</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<div class="col-md-9">
    ${wiki_content}
</div>

<div class="col-md-3">
    <div mod-meta='{
            "tpl": "project/wiki/status.mako",
            "replace": true
        }'></div>
    <div mod-meta='{
            "tpl": "project/wiki/nav.mako",
            "replace": true
        }'></div>

    <div mod-meta='{
            "tpl": "project/wiki/toc.mako",
            "replace": true
        }'></div>

</div>

</%def>
