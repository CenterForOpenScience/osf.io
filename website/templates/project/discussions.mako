<%inherit file="project/project_base.mako"/>

<%def name="title()">${node['title']} Discussions</%def>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako"/>
% endif

<div class="col-sm-3">
    <div class="osf-sidenav hidden-print" role="complementary">
        <ul class="nav bs-sidenav" style="margin: 0;">
            <!-- Total -->
            <li>
                <a href="${node['url']}discussions/">Total
                    % if user['unread_comments']['total'] > 0:
                        <span class="badge pull-right">${user['unread_comments']['total']}</span>
                    % endif
                </a>
            </li>

            <!-- Overview -->
            <li>
                <a href="${node['url']}discussions/overview">Overview
                    % if user['unread_comments']['node'] > 0:
                        <span class="badge pull-right">${user['unread_comments']['node']}</span>
                    % endif
                </a>
            </li>

            <!-- wiki -->
            % if addons:
                % if 'wiki' in addons_enabled:
                    <li>
                        <a href="${node['url']}discussions/wiki">Wiki
                            % if user['unread_comments']['wiki'] > 0:
                                <span class="badge pull-right">${user['unread_comments']['wiki']}</span>
                            % endif
                        </a>
                    </li>
                % endif
            % endif

            <!-- files -->
            <li>
                <a href="${node['url']}discussions/files">Files
                    % if user['unread_comments']['files'] > 0:
                        <span class="badge pull-right">${user['unread_comments']['files']}</span>
                    % endif
                </a>
            </li>
        </ul>
    </div>
</div>

<div class="col-sm-9">
    <div class="discussion">
        % if comment is UNDEFINED:

            <!-- All comments for Overview, Files and Wiki -->
            <h3>
            % if comment_target == 'node':
                Overview
            % else:
                ${comment_target.title()}
            % endif
            </h3>
            <div data-bind="if: discussion().length > 0">
                Show <a data-bind="click: showRecent">recently commented users</a> or
                <a data-bind="click: showFrequent">most frequently commented users</a>
                <span class="pull-right" data-bind="foreach: {data: discussion, afterAdd: setupToolTips}">
                    <a data-toggle="tooltip" data-bind="attr: {href: url, title: fullname}" data-placement="bottom">
                        <img data-bind="attr: {src: gravatarUrl}"/>
                    </a>
                </span>
            </div>
            <div data-bind="if: discussion().length == 0" style="padding-top: 20px;">
                % if comment_target == 'total':
                    There are no comments on this project yet! Go to the
                    <a href="${node['url']}">Overview page,</a> open the comment pane and make a first one!
                % elif comment_target == 'node':
                    There are no comments on the Overview page yet! Go to the
                    <a href="${node['url']}">Overview page,</a> open the comment pane and make a first one!
                % else:
                    There are no comments on the ${comment_target.title()} page yet! Go to the
                    <a href="${node['url']}${comment_target}">${comment_target.title()} page,</a> open the comment pane and make a first one!
                % endif
            </div>

        %else:

            <!-- Comment thread page -->
            <h6>You are viewing a single comment's thread.
            <a data-bind="attr:{href: '${node['url']}'+rootUrl()}">View the rest of the comments in this section</a></h6>
            <a data-bind="attr:{href: '${node['url']}'+parentUrl()}"><h6><i class="icon-caret-up"></i> Parent comment</h6></a>
        % endif
        <div class="comment-list" data-bind="template: {name: 'commentTemplate', foreach: comments}"></div>
        % if not comment is UNDEFINED:
            <div data-bind="if: comments().length == 1">
                <span data-bind="foreach: comments">
                    <span data-bind="ifnot: shouldShow">
                        Comment deleted.
                    </span>
                </span>
            </div>
        % endif
    </div>
</div>

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

<script src=${"/static/public/js/discussions-page.js" | webpack_asset}></script>

</%def>