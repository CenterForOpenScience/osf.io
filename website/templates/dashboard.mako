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
                    <p class="help-block" data-bind="if:tzname">
                        All times displayed at
                        <span data-bind="text:tzname"></span>
                        <a href="http://en.wikipedia.org/wiki/Coordinated_Universal_Time" target="_blank">UTC</a> offset.
                    </p>
                     <dl class="dl-horizontal activity-log"
                        data-bind="foreach: {data: logs, as: 'log'}">
                        <dt><span class="date log-date" data-bind="text: log.localDatetime, tooltip: {title: log.utcDatetime}"></span></dt>
                      <dd class="log-content">
                        <a data-bind="text: log.userFullName || log.apiKey, attr: {href: log.userURL}"></a>
                        <!-- log actions are the same as their template name -->
                        <span data-bind="template: {name: log.action, data: log}"></span>
                      </dd>

                    </dl><!-- end foreach logs -->
                </div><!-- end #logScope -->
            </div><!-- end #watchFeed -->
        </div>
    </div>
</div>

<%include file="log_templates.mako"/>
</%def>

<%def name="javascript_bottom()">
<script>
    // Initiate LogsViewModel
    $logScope = $("#logScope");
    ko.cleanNode($logScope[0]);
    ko.applyBindings(new LogsViewModel($logScope.data("target")), $logScope[0]);
</script>
</%def>
