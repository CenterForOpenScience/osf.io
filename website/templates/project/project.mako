<%inherit file="project/project_base.mako"/>

<%def name="title()">${node['title']}</%def>

<%include file="project/modal_add_pointer.mako"/>

% if node['node_type'] == 'project':
    <%include file="project/modal_add_component.mako"/>
% endif

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako"/>
% endif

<div class="row">

    <div class="col-sm-6">

        % if addons:

            <!-- Show widgets in left column if present -->
            % for addon in addons_enabled:
                % if addons[addon]['has_widget']:
                    %if addon == 'wiki':
                        %if user['show_wiki_widget']:
                            <div class="addon-widget-container" mod-meta='{
                            "tpl": "../addons/wiki/templates/wiki_widget.mako",
                            "uri": "${node['api_url']}wiki/widget/"
                        }'></div>
                        %endif

                    %else:
                    <div class="addon-widget-container" mod-meta='{
                            "tpl": "../addons/${addon}/templates/${addon}_widget.mako",
                            "uri": "${node['api_url']}${addon}/widget/"
                        }'></div>
                    %endif
                % endif
            % endfor

        % else:
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

    <div class="col-sm-6">

        <!-- Citations -->
        % if not node['anonymous']:
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
            </div><!-- end .citations -->
        <hr />
        % endif

        <!-- Show child on right if widgets -->
        % if addons:
            ${children()}
        % endif


        %if node['tags'] or 'write' in user['permissions']:
            <div class="tags">
                <input name="node-tags" id="node-tags" value="${','.join([tag for tag in node['tags']]) if node['tags'] else ''}" />
            </div>
        %endif

        <hr />

        <div class="logs">
            <%include file="log_list.mako"/>
        </div>

    </div>

</div>

<%def name="children()">
    % if node['node_type'] == 'project':
            <div class="pull-right btn-group">
                % if 'write' in user['permissions'] and not node['is_registration']:
                    <a class="btn btn-default" data-toggle="modal" data-target="#newComponent">Add Component</a>
                    <a class="btn btn-default" data-toggle="modal" data-target="#addPointer">Add Links</a>
                % endif
            </div>
        <h2>Components</h2>
        <hr />
    % endif


% if node['node_type'] == 'project':
  % if node['children']:
      <div id="containment">
          <div mod-meta='{
                  "tpl": "util/render_nodes.mako",
                  "uri": "${node["api_url"]}get_children/",
                  "replace": true,
          "kwargs": {"sortable" : ${'true' if not node['is_registration'] else 'false'}}
              }'></div>
      </div>
  % else:
    <p>No components have been added to this project.</p>
  % endif
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

<script type="text/javascript">
    $script(['/static/js/logFeed.js'], 'logFeed');

    $('body').on('nodeLoad', function(event, data) {
       $script.ready('logFeed', function() {
           var logFeed = new LogFeed('#logScope', nodeApiUrl + 'log/');
       });
    });

    ##  NOTE: pointers.js is loaded in project_base.mako
    $script.ready('pointers', function() {
       var pointerManager = new Pointers.PointerManager('#addPointer', contextVars.node.title);
    });


    var $comments = $('#comments');
    var userName = '${user_full_name | js_str}';
    var canComment = ${'true' if user['can_comment'] else 'false'};
    var hasChildren = ${'true' if node['has_children'] else 'false'};

    if ($comments.length) {

        $script(['/static/js/commentpane.js', '/static/js/comment.js'], 'comments');

        $script.ready('comments', function () {
            var timestampUrl = nodeApiUrl + 'comments/timestamps/';
            var onOpen = function() {
                var request = $.osf.putJSON(timestampUrl);
                request.fail(function(xhr, textStatus, errorThrown) {
                    Raven.captureMessage('Could not update comment timestamp', {
                        url: timestampUrl,
                        textStatus: textStatus,
                        errorThrown: errorThrown
                    });
                });
            }
            var commentPane = new CommentPane('#commentPane', {onOpen: onOpen});
            Comment.init('#commentPane', userName, canComment, hasChildren);
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
            interactive: ${'true' if user["can_edit"] else 'false'},
            maxChars: 128,
            onAddTag: function(tag){
                var url = "${node['api_url']}" + "addtag/" + tag + "/";
                var request = $.ajax({
                    url: url,
                    type: "POST",
                    contentType: "application/json"
                });
                request.fail(function(xhr, textStatus, error) {
                    Raven.captureMessage('Failed to add tag', {
                        tag: tag, url: url, textStatus: textStatus, error: error
                    });
                })
            },
            onRemoveTag: function(tag){
                var url = "${node['api_url']}" + "removetag/" + tag + "/";
                var request = $.ajax({
                    url: url,
                    type: "POST",
                    contentType: "application/json"
                });
                request.fail(function(xhr, textStatus, error) {
                    Raven.captureMessage('Failed to remove tag', {
                        tag: tag, url: url, textStatus: textStatus, error: error
                    });
                })
            }
        });

        // Limit the maximum length that you can type when adding a tag
        $('#node-tags_tag').attr("maxlength", "128");

        // Remove delete UI if not contributor
        % if 'write' not in user['permissions'] or node['is_registration']:
            $('a[title="Removing tag"]').remove();
            $('span.tag span').each(function(idx, elm) {
                $(elm).text($(elm).text().replace(/\s*$/, ''))
            });
        % endif

        %if node['is_registration'] and not node['tags']:
            $('div.tags').remove();
        %endif

    });
    $script.ready(['rubeus'], function() {
        // Initialize filebrowser
        var filebrowser = new Rubeus('#myGrid', {
                data: nodeApiUrl + 'files/grid/',
                columns: [Rubeus.Col.Name],
                uploads: false,
                width: "100%",
                height: 600,
                progBar: '#filetreeProgressBar',
                searchInput: '#fileSearch'
        });
    })
</script>

</%def>
