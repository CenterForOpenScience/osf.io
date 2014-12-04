<%page expression_filter="h"/>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title'] | n} Wiki (History)</%def>

<div class="row">
    <div class="col-sm-3">
        <%include file="wiki/templates/nav.mako"/>
        <%include file="wiki/templates/toc.mako"/>
    </div>
    <div class="col-sm-9">
        <%include file="wiki/templates/status.mako"/>
        <div class="row">
            <div class="col-sm-8 wiki">
                ${wiki_content | n}
            </div>
            <div class="col-sm-4">
                <div class="pull-right">
                    <%include file="wiki/templates/history.mako" />
                </div>
            </div>
        </div>
    </div>
</div>

<script type="text/javascript">
    window.onload = function() {
        $('#pageName').append('<h5 style="margin-top:5px"><span>Version: </span>${compare_version}</h5>');
    }
</script>
