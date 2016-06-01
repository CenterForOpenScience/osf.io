<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Analytics</%def>

<div class="page-header visible-xs">
    <h2 class="text-300">Analytics</h2>
</div>

% if not node['is_public']:
    <div class="row m-lg">
        <div class="col-xs-12 text-center">
            <img src="/static/img/no_analytics.png">
        </div>
    </div>
% else:
    <div id="adBlock" class="scripted alert alert-info text-center alert-dismissible" role="alert">
      <button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>
      The use of adblocking software may prevent site analytics from loading properly.
    </div>

    <div class="row m-lg">
        <div class="col-sm-12">
            <div class="panel panel-default">
                <div class="panel-heading clearfix">
                    <h3 class="panel-title">Visits Over Time</h3>
                </div>
                <div id="visits" class="panel-body">
                    <div class="text-center">
                        <div class="logo-spin logo-lg"></div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-sm-6">
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
                        <!-- ko if: referrers().length == 0 -->
                            <h4 class="text-centered">No referrers for this time period.</h4>
                        <!-- /ko -->
                        <!-- ko ifnot: referrers().length == 0 -->
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
                    <!-- /ko -->
                </div>
            </div>
        </div>
        <div class="col-sm-6">
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
                keen: { public: { readKey: ${node['keenio_read_key'] | sjson, n} } }
            })
        </script>
    %endif

    <%def name="javascript_bottom()">
        ${parent.javascript_bottom()}
        <script src="${'/static/public/js/statistics-page.js' | webpack_asset}"></script>

    </%def>

%endif
