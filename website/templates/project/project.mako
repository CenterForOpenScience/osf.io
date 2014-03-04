<%inherit file="project/project_base.mako"/>

<%def name="title()">Project</%def>

    <div class="row">

        <div class="col-md-6">

            % if addons:

                <!-- Show widgets in left column if present -->
                % for addon in addons_enabled:
                    % if addons[addon]['has_widget']:
                        <div class="addon-widget-container" mod-meta='{
                                "tpl": "../addons/${addon}/templates/${addon}_widget.mako",
                                "uri": "${node['api_url']}${addon}/widget/"
                            }'></div>
                    % endif
                % endfor

            % else:

                % if 'wiki' in addons and addons['wiki']['has_widget']:
                    <div class="addon-widget-container" mod-meta='{
                            "tpl": "../addons/wiki/templates/wiki_widget.mako",
                            "uri": "${node['api_url']}wiki/widget/"
                        }'></div>
                % endif

                <!-- If no widgets, show components -->
                ${children()}

            % endif

            <div class="addon-widget-container">
                <h3 class="addon-widget-header"><a href="${node['url']}files/">Files</a></h3>
                <div id="filetreeProgressBar" class="progress progress-striped active">
                    <div class="progress-bar"  role="progressbar" aria-valuenow="100"
                        aria-valuemin="0" aria-valuemax="100" style="width: 100%">
                        <span class="sr-only">Loading</span>
                    </div>
                </div>

                <input role="search" class="form-control" placeholder="Search files..." type="text" id="fileSearch" autofocus>
                <div id="myGrid" class="filebrowser hgrid"></div>
            </div>

        </div>

        <div class="col-md-6">

            <!-- Citations -->
            <div class="citations">
                <span class="citation-label">Citation:</span>
                <span>${node['display_absolute_url']}</span>
                <a href="#" class="citation-toggle" style="padding-left: 10px;">more</a>
                <dl class="citation-list">
                    <dt>APA</dt>
                        <dd class="citation-text">${node['citations']['apa']}</dd>
                    <dt>MLA</dt>
                        <dd class="citation-text">${node['citations']['mla']}</dd>
                    <dt>Chicago</dt>
                        <dd class="citation-text">${node['citations']['chicago']}</dd>
                </dl>
            </div>

            <hr />

            <!-- Show child on right if widgets -->
            % if addons:
                ${children()}
            % endif

            <div class="tags">
                <input name="node-tags" id="node-tags" value="${','.join([tag for tag in node['tags']]) if node['tags'] else ''}" />
            </div>

            <hr />

            <div class="logs">
                <div id='logScope'>
                    <%include file="log_list.mako"/>
                </div><!-- end #logScope -->
                ## Hide More widget until paging for logs is implemented
                ##<div class="paginate pull-right">more</div>
            </div>

        </div>

    </div>

    % if node['can_comment']:

        <div id="comments" class="col-md-6">
            <h2>Comments</h2>
            <div data-bind="template: {name: 'commentTemplate', foreach: displayComments}"></div>
            <div data-bind="if: canComment">
                <div>
                     <i class="icon-comment-alt"></i> Add comment
                </div>
                <div>
                    <select data-bind="options: privacyOptions, optionsText: privacyLabel, value: replyPublic"></select>
                    <span class="comment-author">{{userName}}</span>
                </div>
                <div class="form-group">
                    <textarea class="form-control" data-bind="value: replyContent"></textarea>
                </div>
                <div>
                    <a class="btn btn-default btn-default" data-bind="click: submitReply"><i class="icon-check"></i> Save</a>
                    <a class="btn btn-default btn-default" data-bind="click: cancelReply"><i class="icon-undo"></i> Cancel</a>
                </div>
            </div>
        </div>

    % endif

    <script type="text/html" id="commentTemplate">

        <div class="comment">

            <div>
                <span data-bind="if: editing">
                    <select data-bind="options: privacyOptions, optionsText: privacyLabel, value: isPublic"></select>
                </span>
                <span data-bind="ifnot: editing">
                    <i data-bind="visible: showPrivateIcon" class="icon-lock"></i>
                </span>
                <span class="comment-author">{{author.name}}</span>
                <span class="comment-date pull-right">{{dateModified}}</span>
            </div>

            <div data-bind="ifnot: editing">
                <span data-bind="if: hasChildren">
                    <i data-bind="css: toggleIcon, click: toggle"></i>
                </span>
                <span data-bind="text: content, css: {'edit-comment': editHighlight}, event: {mouseover: startHoverContent, mouseleave: stopHoverContent, dblclick: edit}"></span>
            </div>

            <div data-bind="if: editing">
                <div class="form-group">
                    <textarea class="form-control" data-bind="value: content"></textarea>
                </div>
                <div>
                    <a class="btn btn-default btn-default" data-bind="click: submitEdit"><i class="icon-check"></i> Save</a>
                    <a class="btn btn-default btn-default" data-bind="click: cancelEdit"><i class="icon-undo"></i> Cancel</a>
                </div>
            </div>

            <!-- Action bar -->
            <div data-bind="ifnot: editing">
                <span data-bind="if: $root.canComment, click: showReply">
                    <i class="icon-reply"></i>
                </span>
                <span data-bind="click: reportSpam">
                    <i class="icon-warning-sign"></i>
                </span>
                <span data-bind="if: canDelete, click: remove">
                    <i class="icon-trash"></i>
                </span>
            </div>

            <ul>

                <!-- ko if: showChildren -->
                    <!-- ko template: {name:  'commentTemplate', foreach: displayComments} -->
                    <!-- /ko -->
                <!-- /ko -->

                <!-- ko if: replying -->
                    <div>
                        <select data-bind="options: privacyOptions, optionsText: privacyLabel, value: isPublic"></select>
                        <span class="comment-author">{{userName}}</span>
                    </div>
                    <div>
                        <div class="form-group">
                            <textarea class="form-control" data-bind="value: replyContent"></textarea>
                        </div>
                        <div>
                            <a class="btn btn-default btn-default" data-bind="click: submitReply"><i class="icon-check"></i> Save</a>
                            <a class="btn btn-default btn-default" data-bind="click: cancelReply"><i class="icon-undo"></i> Cancel</a>
                        </div>
                    </div>
                <!-- /ko -->

            </ul>

        </div>

    </script>

<%def name="children()">
<div class="page-header">
    % if node['category'] == 'project':
        <div class="pull-right btn-group">
            % if user['can_edit']:
                <a class="btn btn-default" data-toggle="modal" data-target="#newComponent">Add Component</a>
                <a class="btn btn-default" data-toggle="modal" data-target="#addPointer">Add Links</a>
            % else:
                <a class="btn btn-default disabled">Add Component</a>
                <a class="btn btn-default disabled">Add Link</a>
            % endif
        </div>

    % endif
    <h2>Components</h2>
</div>

% if node['children']:
    <div id="containment">
        <div mod-meta='{
                "tpl": "util/render_nodes.mako",
                "uri": "${node["api_url"]}get_children/",
                "replace": true,
                "kwargs": {"sortable" : true}
            }'></div>
    </div>
% else:
    <p>No components have been added to this project.</p>
% endif

% for name, capabilities in addon_capabilities.iteritems():
    <script id="capabilities-${name}" type="text/html">${capabilities}</script>
% endfor

</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    % for style in addon_widget_css:
        <link rel="stylesheet" href="${style}" />
    % endfor
</%def>

<%def name="javascript_bottom()">
${parent.javascript_bottom()}

% for script in addon_widget_js:
    <script type="text/javascript" src="${script}"></script>
% endfor

<script>

    var $comments = $('#comments');
    var userName = '${user_full_name}';
    var canComment = ${'true' if node['can_comment'] else 'false'};
    var hasChildren = ${'true' if node['has_children'] else 'false'};

    if ($comments.length) {

        $script(['/static/js/comment.js'], 'comment');

        $script.ready('comment', function () {
            Comment.init('#comments', userName, canComment, hasChildren);
        });

    }

</script>

## Todo: Move to project.js
<script>

    $(document).ready(function() {

        // Tooltips
        $('[data-toggle="tooltip"]').tooltip();

        // Tag input
        $('#node-tags').tagsInput({
            width: "100%",
            interactive:${'true' if user["can_edit"] else 'false'},
            onAddTag: function(tag){
                $.ajax({
                    url: "${node['api_url']}" + "addtag/" + tag + "/",
                    type: "POST",
                    contentType: "application/json"
                });
            },
            onRemoveTag: function(tag){
                $.ajax({
                    url: "${node['api_url']}" + "removetag/" + tag + "/",
                    type: "POST",
                    contentType: "application/json"
                });
            }
        });

        // Remove delete UI if not contributor
        % if not user['can_edit']:
            $('a[title="Removing tag"]').remove();
            $('span.tag span').each(function(idx, elm) {
                $(elm).text($(elm).text().replace(/\s*$/, ''))
            });
        % endif

        // Initialize filebrowser
        var filebrowser = new Rubeus('#myGrid', {
                data: nodeApiUrl + 'files/grid/',
                columns: [HGrid.Col.Name],
                uploads: false,
                width: "100%",
                height: 600,
                progBar: '#filetreeProgressBar',
                searchInput: '#fileSearch'
        });

    });

</script>

</%def>
