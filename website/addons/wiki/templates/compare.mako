<%inherit file="base.mako"/>
<%def name="content()">

<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div>
    <div class="col-md-9 wiki">
        ${wiki_content}
    </div>

    <div class="col-md-3">
        <%include file="wiki/templates/nav.mako" />
        <%include file="wiki/templates/history.mako" />
    </div>

</div>
</%def>
