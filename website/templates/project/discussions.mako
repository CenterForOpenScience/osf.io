<%inherit file="project/project_base.mako"/>

<%def name="title()">${node['title']} Discussions</%def>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako"/>
% endif

<div class="col-sm-3">
    <div class="panel panel-default">
        <ul class="nav nav-pills nav-stacked">
            <li role="presentation">
                <a href="${node['url']}discussions/">Overview</a>
            </li>
            <li role="presentation" class="dropdown">
                <a class="dropdown-toggle" data-toggle="dropdown" href="#" role="button" aria-expanded="false">
                    Wiki Pages <span class="caret"></span>
                </a>
                <ul class="dropdown-menu" role="menu" style="min-width: auto; width: 100%">
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
            </li>
        </ul>
    </div>
</div>
<div class="col-sm-9">
    <div class="discussion">
        % if comment is UNDEFINED:
            <h3>
            % if comment_target == 'wiki':
                Wiki
                %if comment_target_id.lower() != 'home':
                    - ${comment_target_id}
                % endif
            % else:
                Overview
            % endif
            </h3>
            <span data-bind="foreach: {data: discussion_by_frequency, afterAdd: setupToolTips}">
                <a data-toggle="tooltip" data-bind="attr: {href: url, title: fullname}" data-placement="bottom">
                    <img data-bind="attr: {src: gravatarUrl}"/>
                </a>
            </span>
            <br>
            <span data-bind="foreach: {data: discussion_by_recency, afterAdd: setupToolTips}">
                <a data-toggle="tooltip" data-bind="attr: {href: url, title: fullname}" data-placement="bottom">
                    <img data-bind="attr: {src: gravatarUrl}"/>
                </a>
            </span>
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