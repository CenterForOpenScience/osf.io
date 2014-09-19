<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Wiki (History)</%def>

<div>
    <div class="col-md-9 wiki">
        ${wiki_content}
    </div>

    <div class="col-md-3">
        <%include file="wiki/templates/nav.mako" />
        <%include file="wiki/templates/history.mako" />
    </div>

</div>
