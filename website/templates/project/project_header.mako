<% import json %>
% if node['is_registration']:
    <div class="alert alert-info">This ${node['category']} is a registration of <a class="alert-link" href="${node['registered_from_url']}">this ${node["category"]}</a>; the content of the ${node["category"]} has been frozen and cannot be edited.
    </div>
    <style type="text/css">
    .watermarked {
        background-image:url('/static/img/read-only.png');
        background-repeat:repeat;
    }
    </style>
% endif

<div id="projectScope">
    <header class="subhead" id="overview">
        <div class="row">

            <div class="col-md-7 cite-container">
                %if parent_node['id']:
                    % if parent_node['is_public'] or parent_node['is_contributor']:
                        <h1 class="node-parent-title">
                            <a href="${parent_node['url']}">${parent_node['title']}</a> /
                        </h1>
                    % else:
                         <h1 class="node-parent-title unavailable">
                             <span>Private Project</span> /
                         </h1>
                    %endif
                %endif
                <h1 class="node-title">
                    <span id="nodeTitleEditable">${node['title']}</span>
                </h1>
            </div><!-- end col-md-->

            <div class="col-md-5">
                <div class="btn-toolbar node-control pull-right">
                    <div class="btn-group">
                    %if not node["is_public"]:
                        <button class='btn btn-default disabled'>Private</button>
                        % if user["is_contributor"]:
                            <a class="btn btn-default" data-bind="click: makePublic">Make Public</a>
                        % endif
                    %else:
                        % if user["is_contributor"]:
                            <a class="btn btn-default" data-bind="click: makePrivate">Make Private</a>
                        % endif
                        <button class="btn btn-default disabled">Public</button>
                    %endif
                    </div><!-- end btn-group -->

                    <div class="btn-group">
                        <a
                            % if user_name and not node['is_registration']:
                                data-bind="click: toggleWatch, tooltip: {title: watchButtonAction, placement: 'bottom'}"
                                class="btn btn-default"
                            % else:
                                class="btn btn-default disabled"
                            % endif
                            href="#">
                                <i class="icon-eye-open"></i>
                                <span data-bind="text: watchButtonDisplay" id="watchCount"></span>
                            </a>

                        <a rel="tooltip" title="Duplicate"
                           class="btn btn-default" href="#"
                           data-toggle="modal" data-target="#duplicateModal"    >
                            <span class="glyphicon glyphicon-share"></span>&nbsp; ${ node['templated_count'] + node['fork_count'] + node['points'] }
                        </a>

                    </div><!-- end btn-grp -->
                </div><!-- end btn-toolbar -->

            </div><!-- end col-md-->

        </div><!-- end row -->


        <p id="contributors">Contributors:
            <div mod-meta='{
                    "tpl": "util/render_contributors.mako",
                    "uri": "${node["api_url"]}get_contributors/",
                    "replace": true
                }'></div>
            % if node['is_fork']:
                <br />Forked from <a class="node-forked-from" href="/${node['forked_from_id']}/">${node['forked_from_display_absolute_url']}</a> on
                <span data-bind="text: dateForked.local, tooltip: {title: dateForked.utc}"></span>
            % endif
            % if node['is_registration'] and node['registered_meta']:
                <br />Registration Supplement:
                % for meta in node['registered_meta']:
                    <a href="${node['url']}register/${meta['name_no_ext']}">${meta['name_clean']}</a>
                % endfor
            % endif
            <br />Date Created:
                <span data-bind="text: dateCreated.local, tooltip: {title: dateCreated.utc}"
                     class="date node-date-created"></span>
            | Last Updated:
            <span data-bind="text: dateModified.local, tooltip: {title: dateModified.utc}"
                   class="date node-last-modified-date"></span>
            % if parent_node['id']:
                <br />Category: <span class="node-category">${node['category']}</span>
            % else:
                 <br />Description: <span id="nodeDescriptionEditable" class="node-description">${node['description']}</span>
            % endif
        </p>

        <nav id="projectSubnav" class="navbar navbar-default ">
            <ul class="nav navbar-nav">
                <li><a href="${node['url']}">Dashboard</a></li>

                <li><a href="${node['url']}files/">Files</a></li>
                <!-- Add-on tabs -->
                % for addon in addons_enabled:
                    % if addons[addon]['has_page']:
                        <li>
                            <a href="${node['url']}${addons[addon]['short_name']}">
                                % if addons[addon]['icon']:
                                    <img src="${addons[addon]['icon']}" class="addon-logo"/>
                                % endif
                                ${addons[addon]['full_name']}
                            </a>
                        </li>
                    % endif
                % endfor

                <li><a href="${node['url']}statistics/">Statistics</a></li>
                % if not node['is_registration']:
                    <li><a href="${node['url']}registrations/">Registrations</a></li>
                % endif
                    <li><a href="${node['url']}forks/">Forks</a></li>
                % if user['can_edit']:
                    <li><a href="${node['url']}settings/">Settings</a></li>
                %endif
            </ul>
        </nav>
    </header>
</div><!-- end projectScope -->

<div class="modal fade" id="duplicateModal">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-body row">
        <div class="col-md-4">
            <h4>
                <div class="input-group">
                    <a class="btn btn-primary form-control">Link to this Project</a>
                    <a class="btn btn-default input-group-addon" href="#showLinks" data-toggle="modal" data-dismiss="modal">
                        ${ node['points'] }
                    </a>
                </div>
            </h4>
            <p>Linking to this projet will reference it in another project, without creating a copy. The link will always point to the most up-to-date version.</p>

        </div>
        <div class="col-md-4">
            <h4>
                <div class="input-group">
                    <a class="btn btn-primary form-control" data-dismiss="modal" onclick="NodeActions.useAsTemplate();">Copy Project Structure</a>
                    <a class="btn btn-default disabled input-group-addon">${ node['templated_count'] }</a>
                </div>
            </h4>
            <p>This option will create a new project, using this project as a template. The new project will be structured in the same way, but contain no data.</p>
        </div>
        <div class="col-md-4">
            <h4>
                <div class="input-group">
                    <a class="btn btn-primary form-control" data-dismiss="modal" onclick="NodeActions.forkNode();">Fork this Project</a>
                    <a class="btn btn-default input-group-addon" href="${ node['url'] }forks/">${ node['fork_count'] }</a>
                </div>
            </h4>
            <p>Fork this project if you plan to build upon it in your own work. The new project will be an exact duplicate of this project's current state, with you as the only contributor.</p>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
      </div>
    </div><!-- /.modal-content -->
  </div><!-- /.modal-dialog -->
</div><!-- /.modal -->
