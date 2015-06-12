<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Statistics</%def>

<div class="row">
    <div class="panel panel-default">
         <div class="panel-heading">
            <h3>Visits</h3>
        </div>
        <div class="panel-body piwikChart"></div>
    </div>
</div>

<script type="text/javascript" src="../../static/js/piwikStats.js"></script>