<%inherit file="project/project_base.mako"/>

<%def name="title()">${node['title']} Discussions</%def>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako"/>
% endif

<div class="col-sm-3">
    <div class="panel panel-default">
        <ul class="nav nav-stacked nav-pills">
            <li><a href="#">Overview</a></li>
            <li><a href="#">Files</a></li>
        </ul>
    </div>
</div>
<div class="col-sm-9">
    <div id="discussion-overview">
        <h3>Overview</h3>
        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>
    </div>
    <div id="discussion-files">
        <h3>Files</h3>
        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>
    </div>
</div>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="javascript_bottom()">
<% import json %>

${parent.javascript_bottom()}

<script src="/static/public/js/discussions-page.js"></script>

</%def>