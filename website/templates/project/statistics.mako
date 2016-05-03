<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Analytics</%def>

<div class="page-header  visible-xs">
    <h2 class="text-300">Analytics</h2>
</div>

<div class="row m-lg">
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Visits</h3>
            </div>
            <div id="visits" class="panel-body">
                <div class="text-center">
                    <div class="logo-spin logo-lg"></div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Top Referrers</h3>
            </div>
            <div id="topReferrers" class="panel-body scripted">
                <!-- ko if: loadRefs -->
                <div class="text-center">
                    <div class="logo-spin logo-lg"></div>
                </div>
                <!-- /ko -->
                <!-- ko ifnot: loadRefs -->
                <table class="table">
                    <thead>
                        <th>Referrer</th>
                        <th>Unique Visitors</th>
                    </thead>
                    <tbody data-bind="foreach: referrers">
                        <td data-bind="text: referrer"></td>
                        <td data-bind="text: count"></td>
                    </tbody>
                </table>
                <!-- /ko -->
            </div>
        </div>
    </div>
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Visits by Server Time</h3>
            </div>
            <div id="serverTimeVisits" class="panel-body">
                <div class="text-center">
                    <div class="logo-spin logo-lg"></div>
                </div>
            </div>
        </div>
    </div>
</div>

%if keen_project_id:
        <script>
            window.contextVars = $.extend(true, {}, window.contextVars, {
                keenReadKey: ${node['keenio_read_key'] | sjson, n}
            })
        </script>
%endif

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
    <script src="${'/static/public/js/statistics-page.js' | webpack_asset}"></script>

</%def>




