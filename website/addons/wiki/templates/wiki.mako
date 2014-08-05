<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Wiki</%def>

<div class="row">
    <div class="col-md-12">
        <%include file="wiki/templates/nav.mako"/>

    <div class="col-md-3">
        <%include file="wiki/templates/toc.mako" />
    </div>
    <div class="col-md-9 wiki">
        ${wiki_content}
    </div>
</div>
    </div>


