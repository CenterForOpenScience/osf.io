<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Wiki</%def>

<div class="row">
    <div class="col-md-3">
        <%include file="wiki/templates/nav.mako" />
        <%include file="wiki/templates/toc.mako" />
    </div>
    <div class="col-md-9">
        <%include file="wiki/templates/status.mako"/>
        ${wiki_content | n}
    </div>
</div>


##<div mod-meta='{
##        "tpl": "metadata/comment_group.mako",
##        "kwargs": {
##            "guid": "${wiki_id}",
##            "top": true
##        },
##        "replace": true
##    }'></div>

