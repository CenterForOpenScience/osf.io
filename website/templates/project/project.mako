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
<% import json %>

${parent.javascript_bottom()}

% for script in addon_widget_js:
    <script type="text/javascript" src="${script}"></script>
% endfor

<script type="text/javascript">
    // Hack to allow mako variables to be accessed to JS modules

    window.contextVars = $.extend(true, {}, window.contextVars, {
        currentUser: {
            name: '${user_full_name | js_str}',
            canComment: ${json.dumps(user['can_comment'])},
            canEdit: ${json.dumps(user['can_edit'])}
        },
        node: {
            hasChildren: ${json.dumps(node['has_children'])},
            isRegistration: ${json.dumps(node['is_registration'])},
            tags: ${json.dumps(node['tags'])}
        }
    });
</script>

<script src="/static/public/js/project-dashboard.js"></script>

% for asset in addon_widget_js:
<script src="${asset}"></script>
% endfor

</%def>
