<%inherit file="project/project_base.mako"/>

<%def name="title()">${node['title']} Discussions</%def>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako"/>
% endif

<div class="col-sm-3">
    <div class="panel panel-default"><!--TODO fix this on the screen -->
        <ul class="nav nav-stacked nav-pills">
            <li><a id="discussion-overview-btn" class="discussion-btn" href="#">Overview</a></li>
            <li><a id="discussion-files-btn" class="discussion-btn" href="#">Files</a></li>
        </ul>
    </div>
</div>
<div class="col-sm-9">
    <div id="discussion-overview" class="discussion">
        <h3>Overview</h3>
        ${newComment()}
        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>
    </div>
    <div id="discussion-files" class="discussion" style="display: none">
        <h3>Files</h3>
        ${newComment()}
        <div data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>
    </div>
</div>

<%def name="newComment()">
    <div class='row' data-bind="if: canComment">
        <button class="btn btn-link" data-bind="click: showReply">Add a comment</button>
    </div>
    <div data-bind="if: replying" style="margin-top: 20px">
        <form class="form">
            <div class="form-group">
                <textarea class="form-control" placeholder="Add a comment"
                          data-bind="value: replyContent, valueUpdate: 'input', attr: {maxlength: $root.MAXLENGTH}"></textarea>
            </div>
            <div>
                <a class="btn btn-default"
                   data-bind="click: submitReply, visible: replyNotEmpty, css: {disabled: submittingReply}"><i
                        class="icon-check"></i> {{saveButtonText}}</a>
                <a class="btn btn-default" data-bind="click: cancelReply, css: {disabled: submittingReply}"><i
                        class="icon-undo"></i> Cancel</a>
                <span data-bind="text: replyErrorMessage" class="comment-error"></span>
            </div>
            <div class="comment-error">{{errorMessage}}</div>
        </form>
    </div>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="javascript_bottom()">
<% import json %>

${parent.javascript_bottom()}

<script src="/static/public/js/discussions-page.js"></script>

</%def>