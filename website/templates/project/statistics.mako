<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Analytics</%def>

<div>
    
</div>

<div class="page-header  visible-xs">
    <h2 class="text-300">Analytics</h2>
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

<%def name="javascript_bottom()">\


</%def>

