<%inherit file="preprints/base.mako"/>
<%def name="title()">Dashboard</%def>
<%def name="content()">
<div class="row">
    <div class="col-md-6">
        <div class="page-header">
            <div class="pull-right"><a class="btn btn-default" href="/preprint/new">New Preprint</a></div>
            <h3>My Preprints</h3>
        </div>
        <div mod-meta='{
                 "tpl": "util/render_nodes.mako",
                 "uri": "/api/v1/preprint/dashboard/get_nodes/",
                 "replace": true
            }'></div>
    </div>
##    <div class="row">
##        <div class="col-md-6">
##           <div id="watchFeed">
##               <div class="page-header">
##                    <h3>Watched Preprints</h3>
##                </div>
##                <div id="logScope">
##                    <%include file="log_list.mako"/>
##                    <a class="moreLogs" data-bind="click: moreLogs, visible: enableMoreLogs">more</a>
##                </div><!-- end #logScope -->
##            </div><!-- end #watchFeed -->
##        </div>
##    </div>
</div>
</%def>

<%def name="javascript_bottom()">
<script>
    // Initialize the LogFeed
    $script(['/static/js/logFeed.js']);
    $script.ready('logFeed', function() {
        var logFeed = new LogFeed("#logScope", "/api/v1/watched/logs/");
    });
</script>
</%def>
