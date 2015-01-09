<%inherit file="project/project_base.mako"/>

<%def name="title()">${node['title']} Discussions</%def>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako"/>
% endif

<div class="col-sm-3">
    <div class="osf-sidenav hidden-print" role="complementary">
        <ul class="nav bs-sidenav" style="margin: 0;">
            <li>
                <a href="${node['url']}discussions/">Overview
                    % if overview_unread > 0:
                        <span class="badge pull-right">${overview_unread}</span>
                    % endif
                </a>
            </li>

            <!-- wiki -->
            % if addons:
                % for addon in addons_enabled:
                    % if addon == 'wiki':
                        <hr/>
                        <li>
                            <h4 style="margin-left: 15px">Wiki</h4>
                        </li>
                        <li>
                            % if wiki_home_content:
                                <a href="${node['url']}discussions/wiki/home">
                                    Home
                                    % if wiki_home_unread > 0:
                                        <span class="badge pull-right">${wiki_home_unread}</span>
                                    % endif
                                </a>
                            % else:
                                <a style="color: #808080">Home (No wiki content)</a>
                            % endif
                        </li>
                        % for page in wiki_pages_current:
                            % if page['name'].lower() != 'home':
                                <li>
                                    <a href="${node['url']}discussions/wiki/${page['name']}">
                                        ${page['name']}
                                        % if page['unread'] > 0:
                                            <span class="badge pull-right">${page['unread']}</span>
                                        % endif
                                    </a>
                                </li>
                            % endif
                        %endfor
                    % endif
                % endfor
            % endif

            <!-- files -->
            <hr/>
            <li>
                <h4 style="margin-left: 15px"">Files</h4>
            </li>
        </ul>
    </div>
</div>

<div class="col-sm-9">
    <div class="discussion">
        % if comment is UNDEFINED:

            <!-- All comments for Overview, Files and Wiki -->
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
            <div data-bind="visible: discussion().length > 0">
                Show <a data-bind="click: showRecent">recently commented users</a> or
                <a data-bind="click: showFrequent">most frequently commented users</a>
                <span class="pull-right" data-bind="foreach: {data: discussion, afterAdd: setupToolTips}">
                    <a data-toggle="tooltip" data-bind="attr: {href: url, title: fullname}" data-placement="bottom">
                        <img data-bind="attr: {src: gravatarUrl}"/>
                    </a>
                </span>
            </div>
            ${newComment()}

        %else:

            <!-- Comment thread page -->
            <h6>You are viewing a single comment's thread.
            <a data-bind="attr:{href: '${node['url']}'+rootUrl()}">View the rest of the comments</a></h6>
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

<!-- Template for making a new comment -->
<%def name="newComment()">
    <div data-bind="if: canComment">
        <span data-bind="ifnot: commented()">
            There are currently no comments on this page yet. Would you like to <a data-bind="click: showReply">make the first one</a>?
        </span>
        <span data-bind="if: commented">
            <a data-bind="click: showReply">
                Add a comment
            </a>
        </span>
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