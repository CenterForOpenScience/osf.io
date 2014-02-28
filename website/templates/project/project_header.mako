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
                %if parent['id']:
                    % if parent['is_public'] or parent['is_contributor']:
                        <h1 class="node-parent-title">
                            <a href="${parent['url']}">${parent['title']}</a> /
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
                            <a class="btn btn-default" id="publicButton" data-target="${node['api_url']}permissions/public/">Make Public</a>
                        % endif
                    %else:
                        % if user["is_contributor"]:
                            <a class="btn btn-default" id="privateButton" data-target="${node['api_url']}permissions/private/">Make Private</a>
                        % endif
                        <button class="btn btn-default disabled">Public</button>
                    %endif
                    </div><!-- end btn-group -->

                    <div class="btn-group">
                        % if user_name and not node['is_registration']:
                            <a rel="tooltip" title="Watch" class="btn btn-default" href="#" data-bind="click: toggleWatch">
                        % else:
                            <a rel="tooltip" title="Watch" class="btn btn-default disabled" href="#">
                        % endif
                        <i class="icon-eye-open"></i>
                        <span data-bind="text: watchButtonDisplay" id="watchCount"></span>

                        </a>

                        <a
                            rel="tooltip"
                            title="Number of times this ${node['category']} has been forked (copied)"
                            % if node["category"] == 'project' and not node['is_registration'] and user_name:
                                href="#"
                                class="btn btn-default node-fork-btn"
                                onclick="NodeActions.forkNode();"
                            % else:
                                class="btn btn-default disabled node-fork-btn"
                            % endif
                        >
                            <i class="icon-code-fork"></i>&nbsp;${node['fork_count']}
                        </a>
##                        <a
##                                rel="tooltip"
##                                % if node['points']:
##                                    href="#showLinks"
##                                    data-toggle="modal"
##                                % endif
##                                class="btn btn-default ${'disabled' if node['points'] == 0 else ''}"
##                                title="Number times this ${node['category']} has been linked"
##                            >
##                            <i id="linkCount" class="icon-hand-right">&nbsp;${node['points']}</i>
##                        </a>

                    </div><!-- end btn-grp -->
                </div><!-- end btn-toolbar -->

            </div><!-- end col-md-->

        </div><!-- end row -->


        <p id="contributors">Contributors:
            <span id="contributorsview"><div mod-meta='{
                    "tpl": "util/render_contributors.mako",
                    "uri": "${node["api_url"]}get_contributors/",
                    "replace": true
                }'></div></span>
            % if node['is_fork']:
                <br />Forked from <a class="node-forked-from" href="/${node['forked_from_id']}/">${node['forked_from_display_absolute_url']}</a> on
                <span data-bind="text: dateForked.local,
                                tooltip: {title: dateForked.utc}"></span>
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
            % if parent['id']:
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
                % if user['is_contributor'] and not node['is_registration']:
                <li><a href="${node['url']}contributors/">Contributors</a></li>
                %endif
                % if user['is_contributor'] and not node['is_registration']:
                <li><a href="${node['url']}settings/">Settings</a></li>
                %endif
            </ul>
        </nav>
    </header>
</div><!-- end projectScope -->
<%include file="modal_add_contributor.mako"/>
<%include file="modal_add_pointer.mako"/>
<%include file="modal_show_links.mako"/>
## TODO: Find a better place to put this initialization code
<script>
// TODO: pollution! namespace me
    var userId = '${user_id}';
    var nodeId = '${node['id']}';
    var userApiUrl = '${user_api_url}';
    var nodeApiUrl = '${node['api_url']}';

    $(document).ready(function(){

        $logScope = $('#logScope');
        if ($logScope.length > 0) {
            progressBar = $('#logProgressBar')
            progressBar.show();
        }
        // Get project data from the server and initiate the ProjectViewModel
        $.ajax({
            type: 'get',
            url: nodeApiUrl,
            contentType: 'application/json',
            dataType: 'json',
            cache: false,
            success: function(data){
                // Initialize ProjectViewModel with returned data
                ko.applyBindings(new ProjectViewModel(data), $('#projectScope')[0]);

                if (data.user.can_edit) {
                    // Initiate AddContributorViewModel
                    var $addContributors = $('#addContributors');
                    addContribVM = new AddContributorViewModel(
                        data.node.title,
                        data.parent.id,
                        data.parent.title
                    );
                    ko.applyBindings(addContribVM, $addContributors[0]);
                    // Clear user search modal when dismissed; catches dismiss by escape key
                    // or cancel button.
                    $addContributors.on('hidden.bs.modal', function() {
                        addContribVM.clear();
                    });
                }

                // Initialize LogsViewModel when appropriate
                if ($logScope.length > 0) {
                    progressBar.hide();
                    var logs = data['node']['logs'];
                    // Create an array of Log model objects from the returned log data
                    var logModelObjects = createLogs(logs);
                    ko.applyBindings(new LogsViewModel(logModelObjects), $logScope[0]);
                }
            }
        });
    });

    var $addPointer = $('#addPointer');
    var addPointerVM = new AddPointerViewModel(${json.dumps(node['title'])});
    ko.applyBindings(addPointerVM, $addPointer[0]);
    $addPointer.on('hidden.bs.modal', function() {
        addPointerVM.clear();
    });

    var linksModal = $('#showLinks')[0];
    var linksVM = new LinksViewModel(linksModal);
    ko.applyBindings(linksVM, linksModal);


</script>
% if node.get('is_public') and node.get('piwik_site_id'):
<script type="text/javascript">
    $(function() {
        // Note: Don't use cookies for global site ID; cookies will accumulate
        // indefinitely and overflow uwsgi header buffer.
        trackPiwik('${ piwik_host }', ${ node['piwik_site_id'] });
    });
</script>
% endif
