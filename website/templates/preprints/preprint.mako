<%inherit file="project/project_base.mako"/>
##<%inherit file="base.mako"/>
##<%include file="project/project_header.mako"/>

<%def name="title()">Preprint</%def>

% if user['can_comment'] or node['has_comments']:
    <%include file="include/comment_template.mako" />
% endif

<div class="row">

    <div class="col-md-12">

        <p>pdf download link goes here</p>

        <p>option to upload another version for authors</p>

        <p>version history here     </p>

    </div>

    <div class="col-md-12">
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

        <div class="tags">
            <input name="node-tags" id="node-tags" value="${','.join([tag for tag in node['tags']]) if node['tags'] else ''}" />
        </div>

        <hr />

        <div class="logs">
            <div id='logScope'>
                <%include file="log_list.mako"/>
                <a class="moreLogs" data-bind="click: moreLogs, visible: enableMoreLogs">more</a>
            </div><!-- end #logScope -->
            ## Hide More widget until paging for logs is implemented
            ##<div class="paginate pull-right">more</div>
        </div>

    </div>

</div>

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

    var $comments = $('#comments');
    var userName = '${user_full_name}';
    var canComment = ${'true' if user['can_comment'] else 'false'};
    var hasChildren = ${'true' if node['has_children'] else 'false'};

    if ($comments.length) {

        $script(['/static/js/commentpane.js', '/static/js/comment.js'], 'comments');

        $script.ready('comments', function () {
            var commentPane = new CommentPane('#commentPane');
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
        % if 'write' not in user['permissions']:
            $('a[title="Removing tag"]').remove();
            $('span.tag span').each(function(idx, elm) {
                $(elm).text($(elm).text().replace(/\s*$/, ''))
            });
        % endif


    });
</script>

</%def>
