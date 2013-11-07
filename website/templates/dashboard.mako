<%inherit file="base.mako"/>
<%def name="title()">Dashboard</%def>
<%def name="content()">
<div mod-meta='{"tpl": "include/subnav.mako", "replace": true}'></div>

<div class="row">
    <div class="col-md-6">
        <div class="page-header">
            <div class="pull-right"><a class="btn btn-default" href="/project/new">New Project</a></div>
            <h3>Projects</h3>
        </div>
        <div mod-meta='{
                 "tpl": "util/render_nodes.mako",
                 "uri": "/api/v1/dashboard/get_nodes/",
                 "replace": true
            }'></div>
    </div>
    <div class="row">
        <div class="col-md-6">
           <div id="watchFeed">
               <div class="page-header">
                <h3>Watched Projects</h3>
                </div>
                <div id="logScope" data-target="/api/v1/watched/logs/">
                     <dl class="dl-horizontal activity-log"
                        data-bind="foreach: {data: logs, as: 'log'}">
                      <div data-bind="template: {name: 'logTemplate', data: log}"></div>
                    </dl><!-- end foreach logs -->
                </div><!-- end #logScope -->
            </div><!-- end #watchFeed -->
        </div>
    </div>
</div>

<%include file="log_template.mako"/>
</%def>

<%def name="javascript_bottom()">
<script>
    // Initiate LogsViewModel
    $logScope = $("#logScope");
    ko.cleanNode($logScope[0]);
    ko.applyBindings(new LogsViewModel($logScope.data("target")), $logScope[0]);
</script>
</%def>
