% if node_is_registration:
    <div class="alert alert-info">This node is a registration of <a class="alert-link" href="${node_registered_from_url}">this node</a>; the content of the node has been frozen and cannot be edited.
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
            <div class="btn-toolbar pull-right">
                <div class="btn-group">
                %if not node_is_public:
                    <button class='btn btn-default disabled'>Private</button>
                    % if user_is_contributor:
                        <a class="btn btn-primary" id="publicButton" data-target="${node_api_url}permissions/public/">Make public</a>
                    % endif
                %else:
                    % if user_is_contributor:
                        <a class="btn btn-default" id="privateButton" data-target="${node_api_url}permissions/private/">Make private</a>
                    % endif
                    <button class="btn btn-primary disabled">Public</button>
                %endif
                </div><!-- end btn-group -->

                <div class="btn-group">
                    % if user_name:
                        <a rel="tooltip" title="Watch" class="btn btn-default" href="#" data-bind="click: toggleWatch">
                    % else:
                        <a rel="tooltip" title="Watch" class="btn btn-default disabled" href="#">
                    % endif
                    <i class="icon-eye-open"></i>
                    <span data-bind="text: projects()[0].watchButtonDisplay" id="watchCount"></span>

                    </a>


                    <a
                        rel="tooltip"
                        title="Number of times this node has been forked (copied)"
                        % if node_category == 'project' and user_name:
                            href="#"
                            class="btn btn-default node-fork-btn"
                            onclick="NodeActions.forkNode();"
                        % else:
                            class="btn btn-default disabled node-fork-btn"
                        % endif
                    >
                        <i class="icon-code-fork"></i>&nbsp;${node_fork_count}
                    </a>

                </div><!-- end btn-grp -->
            </div><!-- end btn-toolbar -->


            <div class="col-md-8">
                %if parent_id:
                    <h1 style="display:inline-block" class="node-parent-title">
                        <a href="/project/${parent_id}/">${parent_title}</a> /
                    </h1>
                %endif
                <h1 id="${'node-title-editable' if user_can_edit else 'node-title'}" class='node-title' style="display:inline-block">${node_title}</h1>
            </div>

        </div><!-- end row -->


        <p id="contributors">Contributors:
            <div mod-meta='{
                    "tpl": "util/render_contributors.mako",
                    "uri": "${node_api_url}get_contributors/",
                    "replace": true
                }'></div>
            % if node_is_fork:
                <br />Forked from <a class="node-forked-from" href="${node_forked_from_url}">${node_forked_from_url}</a> on ${node_forked_date}
            % endif
            % if node_is_registration and node_registered_meta:
                <br />Registration Supplement:
                % for meta in node_registered_meta:
                    <a href="${node_url}register/${meta['name_no_ext']}">${meta['name_clean']}</a>
                % endfor
            % endif
            <br />Date Created:
                <span class="date node-date-created">${node_date_created}</span>
            | Last Updated:
            <span class="date node-last-modified-date">${node_date_modified}</span>

            % if node:
                <br />Category: <span class="node-category">${node_category}</span>
            % else:
                % if node_description:
                    <br />Description: <span class="node-description">${node_description}</span>
                % endif
            % endif
        </p>

        <nav id="projectSubnav" class="navbar navbar-default ">
            <ul class="nav navbar-nav">
                <li><a href="${node_url}">Dashboard</a></li>
                <li><a href="${node_url}wiki/">Wiki</a></li>
                <li><a href="${node_url}statistics/">Statistics</a></li>
                <li><a href="${node_url}files/">Files</a></li>
                % if not node_is_registration:
                <li><a href="${node_url}registrations/">Registrations</a></li>
                %endif
                <li><a href="${node_url}forks/">Forks</a></li>
                % if user_is_contributor and not node_is_registration:
                <li><a href="${node_url}settings/">Settings</a></li>
                %endif
            </ul>
        </nav>
    </header>
</div>
<%include file="modal_add_contributor.mako"/>
## TODO: Find a better place to put this initialization code
<script>
    $(document).ready(function(){
        // Initiate addContributorsModel
        var $addContributors = $('#addContributors');
        viewModel = new AddContributorViewModel();
        ko.applyBindings(viewModel, $addContributors[0]);
        // Clear user search modal when dismissed; catches dismiss by escape key
        // or cancel button.
        $addContributors.on('hidden', function() {
            viewModel.clear();
        });
        ko.applyBindings(new ProjectViewModel(), $("#projectScope")[0]);
    });
</script>
