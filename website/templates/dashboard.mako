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
                    <%include file="log_list.mako"/>
                </div><!-- end #logScope -->
            </div><!-- end #watchFeed -->
        </div>
    </div>
</div>

</%def>

<%def name="javascript_bottom()">
<script>
    // Initiate LogsViewModel
    $logScope = $("#logScope");
    ko.cleanNode($logScope[0]);
    progressBar = $("#logProgressBar")
    progressBar.show();
    $.ajax({
        url: $logScope.data("target"),
        type: "get", contentType: "application/json",
        dataType: "json",
        cache: false,
        success: function(data){
            // Initialize LogViewModel
            var logs = data['logs'];
            var mappedLogs = $.map(logs, function(item) {
                return new Log({
                    "action": item.action,
                    "date": item.date,
                    "nodeCategory": item.category,
                    "contributor": item.contributor,
                    "contributors": item.contributors,
                    "nodeUrl": item.node_url,
                    "userFullName": item.user_fullname,
                    "userURL": item.user_url,
                    "apiKey": item.api_key,
                    "params": item.params,
                    "nodeTitle": item.node_title,
                    "nodeDescription": item.params.description_new
                })
            });
            $logScope = $("#logScope");
            ko.cleanNode($logScope[0]);
            progressBar.hide();
            ko.applyBindings(new LogsViewModel(mappedLogs), $logScope[0]);
        }
    });
</script>
</%def>
