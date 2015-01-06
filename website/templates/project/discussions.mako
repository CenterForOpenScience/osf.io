<%inherit file="project/project_base.mako"/>

<%def name="title()">${node['title']} Discussions</%def>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako"/>
% endif

<div class="col-sm-3">
    <div class="panel panel-default"><!--TODO fix this on the screen -->
        <ul class="nav bs-sidenav" style="margin: 0;">
            <li><a id="discussion-overview-btn" class="discussion-btn" href="${node['url']}discussions/">Overview</a></li>

        <h4 style="margin-left: 10px;" class="node-category">Wiki Pages</h4>
            <li>
                <a href="${node['url']}discussions/wiki/home">Home</a>
            </li>
            % for page in wiki_pages_current:
                %if page != 'home':
                    <li>
                        <a href="${node['url']}discussions/wiki/${page}">${page}</a>
                    </li>
                % endif
            %endfor
        </ul>
    </div>
</div>
<div class="col-sm-9">
    <div class="discussion">
        % if comment is UNDEFINED:
            <h3>Overview</h3>
            ${newComment()}
        %else:
            <h6>You are viewing a single comment's thread.</h6>
        % endif
        <div class="comment-list" data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>
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
<script>
        % if comment is UNDEFINED:
            window.contextVars.comment = {};
        %else:
            window.contextVars.comment = ${json.dumps(comment)};
        % endif

        window.contextVars.comment_target = '${comment_target}';
        window.contextVars.comment_target_id = '${comment_target_id}';
</script>

<script src="/static/public/js/discussions-page.js"></script>

</%def>