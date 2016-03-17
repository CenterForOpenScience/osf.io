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
    <script src="${"/static/public/js/statistics-page.js" | webpack_asset}"> </script>
    <div id="adBlock" class="scripted alert alert-info text-center alert-dismissible" role="alert">
      <button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>
      The use of adblocking software may prevent site analytics from loading properly.
    </div>

<div class="row">
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Analytics</h3>
            </div>
            <div id="visits" class="panel-body">
            </div>
        </div>
    </div>
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Analytics</h3>
            </div>
            <div id="referrers" class="panel-body">
            </div>
        </div>
    </div>
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Analytics</h3>
            </div>
            <div id="serverVisits" class="panel-body">
            </div>
        </div>
    </div>
</div>
% endif

<%def name="javascript_bottom()">
</%def>
