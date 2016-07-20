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

        <div id="dateRange" class="pull-right">
          Showing analytics from <span class="m-l-xs text-bigger f-w-xl logo-spin logo-sm" id="startDateString"></span>
          until <span class="m-l-xs text-bigger f-w-xl logo-spin logo-sm" id="endDateString"></span>
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
    <div class="row m-lg">
        <div class="col-sm-6">
            <div class="panel panel-default project-analytics">
                <div class="panel-heading clearfix">
                    <h3 class="panel-title">Unique visits</h3>
                </div>
                <div id="visits" class="panel-body">
                    <div class="text-center">
                        <div class="logo-spin logo-lg"></div>
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
                <div class="logo-spin logo-lg"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="col-sm-6">
            <div class="panel panel-default project-analytics">
                <div class="panel-heading clearfix">
                    <h3 class="panel-title">Top referrers</h3>
                </div>
                <div id="topReferrers" class="panel-body">
                    <div class="text-center">
                        <div class="logo-spin logo-lg"></div>
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
                        <div class="logo-spin logo-lg"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

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
