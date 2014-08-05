<%inherit file="base.mako"/>
<%def name="content()">

<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<div class="wiki">
    <div class="row">
        <%include file="wiki/templates/nav.mako"/>
        <div class="col-md-3">
            <%include file="wiki/templates/toc.mako"/>
        </div>

        <div class="col-md-6 wiki">

            ${wiki_content}
        </div>

        <div class="col-md-3">
            <%include file="wiki/templates/history.mako" />
        </div>

    </div>
</div>
</%def>
