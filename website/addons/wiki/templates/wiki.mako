<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Wiki</%def>

<div class="row">
    <div class="col-md-3">
        <%include file="wiki/templates/nav.mako"/>
        <%include file="wiki/templates/toc.mako" />
    </div>
    <div class="col-md-9">
        <%include file="wiki/templates/status.mako"/>
        ${wiki_content}
    </div>
</div>



