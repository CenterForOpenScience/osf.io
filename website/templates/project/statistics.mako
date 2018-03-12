<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Analytics</%def>
<%namespace name="render_nodes" file="util/render_nodes.mako" />

<div class="page-header visible-xs">
    <h2 class="text-300">Analytics</h2>
</div>

<div class="row equal-heighted-row">
    <div class="col-sm-4 col-xs-12 panel panel-default">
        <div class="panel-body">
            <div class="text-center">
                <h3>Forks</h3>
                <h2>${node['fork_count']}</h2>
                <a href='${node['url']}forks'><h4 >View all forks</h4></a>
            </div>
        </div>
    </div>
    <div class="col-sm-4 col-xs-12">
        <div class="panel panel-default">
            <div class="panel-body">
                <div class="text-center">
                    <h3>Links to Project</h3>
                    <h2>${node['linked_nodes_count']}</h2>
                    <a data-toggle="modal" data-target="#showLinks"><h4 >View all links</h4></a>
                </div>
            </div>
        </div>
    </div>
    <div class="col-sm-4 col-xs-12 panel panel-default">
        <div class="panel-body">
            <div class="text-center">
                <h3>Template Copies</h3>
                <h2>${node['templated_count']}</h2>
            </div>
        </div>
    </div>
</div>

% if not node['is_public']:
    <div class="row m-lg">
        <div class="col-xs-12 no-analytics">
          <p>
            Analytics are not available for private projects. To view
            Analytics, make your project public by selecting Make
            Public from the project overview page. Public projects:
          </p>

          <ul>
            <li>are discoverable</li>
            <li>are citable</li>
            <li>can be affiliated with OSF for Institutions partners</li>
            <li>promote open practices among peers</li>
          </ul>

          <p>
            Receive data on visitors to your project by enabling
            Analytics and begin discovering the impact of your work.
          </p>

          <img class="img-responsive center-block" src="/static/img/no_analytics.png">
        </div>
    </div>
% else:
    <div id="adBlock" class="scripted alert alert-info text-center alert-dismissible" role="alert">
      <button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>
      The use of adblocking software may prevent site analytics from loading properly.
    </div>

    % if keen['public']['project_id']:
    <div class="row m-b-sm">
      <div class="col-sm-12">

        <div id="dateRange" class="pull-right">
          Showing analytics from
          <span class="m-l-xs text-bigger f-w-xl ball-pulse ball-pulse-small ball-scale-blue" id="startDateString">
            <div></div>
            <div></div>
            <div></div>
          </span>
          until
          <span class="m-l-xs text-bigger f-w-xl ball-pulse ball-pulse-small ball-scale-blue" id="endDateString">
            <div></div>
            <div></div>
            <div></div>
          </span>
          <button class="btn btn-default m-l-xs" id="showDateRangeForm">Update</button>
        </div>

        <form class="form-inline pull-right hidden" id="dateRangeForm">
          <div class="form-group">
            <label for="startDatePicker">From</label>
            <input type="text" class="form-control" id="startDatePicker">
          </div>
          <div class="form-group m-l-sm">
            <label for="endDatePicker">Until</label>
            <input type="text" class="form-control" id="endDatePicker">
          </div>
          <button type="submit" class="btn btn-default">Update date range</button>
        </form>

      </div>
    </div>

    <div class="row">
        <div class="col-sm-6">
            <div class="panel panel-default project-analytics">
                <div class="panel-heading clearfix">
                    <h3 class="panel-title">Unique visits</h3>
                </div>
                <div id="visits" class="panel-body">
                    <div class="text-center">
                        <div class="ball-pulse ball-scale-blue text-center">
                          <div></div>
                          <div></div>
                          <div></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-sm-6">
          <div class="panel panel-default project-analytics">
            <div class="panel-heading clearfix">
              <h3 class="panel-title">Time of day of visits</h3>
            </div>
            <div id="serverTimeVisits" class="panel-body">
              <div class="text-center">
                  <div class="ball-pulse ball-scale-blue text-center">
                    <div></div>
                    <div></div>
                    <div></div>
                  </div>
              </div>
            </div>
          </div>
        </div>
    </div>

    <div class="row">
        <div class="col-sm-6">
            <div class="panel panel-default project-analytics">
                <div class="panel-heading clearfix">
                    <h3 class="panel-title">Top referrers</h3>
                </div>
                <div id="topReferrers" class="panel-body">
                    <div class="text-center">
                        <div class="ball-pulse ball-scale-blue text-center">
                          <div></div>
                          <div></div>
                          <div></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-sm-6">
            <div class="panel panel-default project-analytics">
                <div class="panel-heading clearfix">
                    <h3 class="panel-title">Popular pages</h3>
                </div>
                <div id="popularPages" class="panel-body">
                    <div class="text-center">
                        <div class="ball-pulse ball-scale-blue text-center">
                          <div></div>
                          <div></div>
                          <div></div>
                        </div>
                    </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    % else:
    <div class="alert alert-danger" role="alert">
      Analytics unavailable. Please contact <a href="mailto:${osf_support_email}">${osf_support_email}</a> if the problem persists.
    </div>
    % endif
%endif

<%def name="stylesheets()">
  ${parent.stylesheets()}
  <link rel="stylesheet" href="/static/css/pages/statistics-page.css">
</%def>

<%def name="javascript_bottom()">
  ${parent.javascript_bottom()}
  <script>
      window.contextVars.analyticsMeta = $.extend(true, {}, window.contextVars.analyticsMeta, {
          pageMeta: {
              title: 'Analytics',
              public: true,
          },
      });
  </script>
  % if keen['public']['project_id'] and node['is_public']:
    <script>
     window.contextVars = $.extend(true, {}, window.contextVars, {
         keen: { public: { readKey: ${node['keenio_read_key'] | sjson, n} } }
     });
    </script>
    <script src="${'/static/public/js/statistics-page.js' | webpack_asset}"></script>
  % endif
</%def>
