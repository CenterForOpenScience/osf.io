<div class="container">

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

<style>
    .modal-subheader {
        font-size: 30px;
        margin-right: 10px;
    }
    .disabled {
        cursor: default !important;
        pointer-events: none;
    }
</style>


<div id="projectScope">
    <header class="subhead" id="overview">
        <div class="row">
            <div class="btn-toolbar pull-right">
                <div class="btn-group">
                %if not node["is_public"]:
                    <button class='btn btn-default disabled'>Private</button>
                    % if user["is_contributor"]:
                        <a class="btn btn-default" id="publicButton" data-target="${node['api_url']}permissions/public/">Make public</a>
                    % endif
                %else:
                    % if user["is_contributor"]:
                        <a class="btn btn-default" id="privateButton" data-target="${node['api_url']}permissions/private/">Make private</a>
                    % endif
                    <button class="btn btn-default disabled">Public</button>
                %endif
                </div><!-- end btn-group -->

                <div class="btn-group">
                    % if user_name:
                        <a rel="tooltip" title="Watch" class="btn btn-default" href="#" data-bind="click: toggleWatch">
                    % else:
                        <a rel="tooltip" title="Watch" class="btn btn-default disabled" href="#">
                    % endif
                    <i class="icon-eye-open"></i>
                    <span data-bind="text: watchButtonDisplay" id="watchCount"></span>

                    </a>


                    <a
                        rel="tooltip"
                        title="Number of times this node has been forked (copied)"
                        % if node["category"] == 'project' and user_name:
                            href="#"
                            class="btn btn-default node-fork-btn"
                            onclick="NodeActions.forkNode();"
                        % else:
                            class="btn btn-default disabled node-fork-btn"
                        % endif
                    >
                        <i class="icon-code-fork"></i>&nbsp;${node['fork_count']}
                    </a>

                </div><!-- end btn-grp -->
            </div><!-- end btn-toolbar -->


            <div class="col-md-8">
                %if parent['id']:
                    <h1 style="display:inline-block" class="node-parent-title">
                        <a href="/project/${parent['id']}/">${parent['title']}</a> /
                    </h1>
                %endif
                <h1 id="${'node-title-editable' if user['can_edit'] else 'node-title'}" class='node-title' style="display:inline-block">${node['title']}</h1>
            </div>

        </div><!-- end row -->


        <p id="contributors">Contributors:
            <div mod-meta='{
                    "tpl": "util/render_contributors.mako",
                    "uri": "${node["api_url"]}get_contributors/",
                    "replace": true
                }'></div>
            % if node['is_fork']:
                <br />Forked from <a class="node-forked-from" href="${node['forked_from_url']}">${node['forked_from_url']}</a> on ${node['forked_date']}
            % endif
            % if node['is_registration'] and node['registered_meta']:
                <br />Registration Supplement:
                % for meta in node['registered_meta']:
                    <a href="${node['url']}register/${meta['name_no_ext']}">${meta['name_clean']}</a>
                % endfor
            % endif
            <br />Date Created:
                <span data-bind="text: dateCreated.local,
                                tooltip: {title: dateCreated.utc}"
                     class="date node-date-created"></span>
            | Last Updated:
            <span data-bind="text: dateModified.local,
                            tooltip: {title: dateModified.utc}"
                   class="date node-last-modified-date"></span>
            % if node:
                <br />Category: <span class="node-category">${node['category']}</span>
            % else:
                % if node['description']:
                    <br />Description: <span class="node-description">${node['description']}</span>
                % endif
            % endif
        </p>

        <nav id="projectSubnav" class="navbar navbar-default ">
            <ul class="nav navbar-nav">
                <li><a href="${node['url']}">Dashboard</a></li>
                <li><a href="${node['url']}wiki/">Wiki</a></li>
                <li><a href="${node['url']}statistics/">Statistics</a></li>
                <li><a href="${node['url']}files/">Files</a></li>
                <li><a href="${node['url']}registrations/">Registrations</a></li>
                <li><a href="${node['url']}forks/">Forks</a></li>
                % if user['is_contributor'] and not node['is_registration']:
                <li><a href="${node['url']}settings/">Settings</a></li>
                %endif
            </ul>
        </nav>
    </header>
</div><!-- end projectScope -->
<%include file="modal_add_contributor.mako"/>
## TODO: Find a better place to put this initialization code
<script>
    $(document).ready(function(){
        // Initiate addContributorsModel
        var $addContributors = $('#addContributors');
        // TODO: Title and parent should be retrieved from AJAX, not mako
        viewModel = new AddContributorViewModel('${node["title"]}', '${parent["id"]}', '${parent["title"]}');
        ko.applyBindings(viewModel, $addContributors[0]);
        // Clear user search modal when dismissed; catches dismiss by escape key
        // or cancel button.
        $addContributors.on('hidden', function() {
            viewModel.clear();
        });

        // Get project data from the server and initiate the ProjectViewModel
        $.ajax({
            url: nodeToUseUrl(),
            type: "get", contentType: "application/json",
            dataType: "json",
            cache: false,
            success: function(data){
                // Initialize ProjectViewModel with returned data
                ko.applyBindings(new ProjectViewModel(data), $("#projectScope")[0]);
            }
        });
    });
</script>
</div><!-- end container -->
