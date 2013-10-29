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

<script>
    /////////////////////
    // Knockout Models //
    /////////////////////
    var addContributorModel = function(initial) {

        var self = this;

        self.query = ko.observable('');
        self.results = ko.observableArray(initial);
        self.selection = ko.observableArray([]);

        self.search = function() {
            $.getJSON(
                '/api/v1/user/search/',
                {query: self.query()},
                function(result) {
                    self.results(result);
                }
            )
        };

        self.addTips = function(elements, data) {
            elements.forEach(function(element) {
                $(element).find('.contrib-button').tooltip();
            });
        };

        self.add = function(data, element) {
            self.selection.push(data);
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.remove = function(data, element) {
            self.selection.splice(
                self.selection.indexOf(data), 1
            );
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.selected = function(data) {
            for (var idx=0; idx < self.selection().length; idx++) {
                if (data.id == self.selection()[idx].id)
                    return true;
            }
            return false;
        };

        self.submit = function() {
            var user_ids = self.selection().map(function(elm) {
                return elm.id;
            });
            $.ajax(
                nodeToUseUrl() + '/addcontributors/',
                {
                    type: 'post',
                    data: JSON.stringify({user_ids: user_ids}),
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        if (response.status === 'success') {
                            window.location.reload();
                        }
                    }
                }
            )
        };

        self.clear = function() {
            self.query('');
            self.results([]);
            self.selection([]);
        };

    };

    var $addContributors = $('#addContributors');

    viewModel = new addContributorModel();
    ko.applyBindings(viewModel, $addContributors[0]);

    // Clear user search modal when dismissed; catches dismiss by escape key
    // or cancel button.
    $addContributors.on('hidden', function() {
        viewModel.clear();
    });
</script>

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
            </div>

            <div class="btn-group">
                % if user_name:
                    <a rel="tooltip" title="Watch" class="btn btn-default" href="#" onclick="NodeActions.toggleWatch()">
                % else:
                    <a rel="tooltip" title="Watch" class="btn btn-default disabled" href="#">
                % endif

                    <i class="icon-eye-open"></i>
                    % if not user_is_watching:
                        <span id="watchCount">Watch&nbsp;${node_watched_count}</span>
                    % else:
                        <span id="watchCount">Unwatch&nbsp;${node_watched_count}</span>
                    % endif

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
        </div>

        <div class="col-md-8">
            %if parent_id:
                <h1 style="display:inline-block" class="node-parent-title">
                    <a href="/project/${parent_id}/">${parent_title}</a> /
                </h1>
            %endif
            <h1 id="${'node-title-editable' if user_can_edit else 'node-title'}" class='node-title' style="display:inline-block">${node_title}</h1>
        </div>

    </div>


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

</header>
    <nav class="navbar navbar-default ">

        <ul class="nav navbar-nav">
            <li><a href="${node_url}">Dashboard</a></li>
            <li><a href="${node_url}wiki/">Wiki</a></li>
            <li><a href="${node_url}statistics/">Statistics</a></li>
            <li><a href="${node_url}files/">Files</a></li>
            <li><a href="${node_url}registrations/">Registrations</a></li>
            <li><a href="${node_url}forks/">Forks</a></li>
            % if user_is_contributor and not node_is_registration:
            <li><a href="${node_url}settings/">Settings</a></li>
            %endif
        </ul>
    </nav>
</header>

<div class="modal fade" id="addContributors" role="dialog" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Add Contributors</h3>
            </div>
            <div class="modal-body">
                <!-- Search box -->
                <form class="form-inline">
                    <input data-bind="value:query" />
                    <button class="btn btn-default" data-bind="click:search">Search</button>
                </form>
                <div class="row">
                    <div class="col-md-6">
                        <h3>Search Results</h3>
                        <table>
                            <tbody data-bind="foreach:{data:results, afterRender:addTips}">
                                <tr class="search-contributor-result" data-bind="if:!($root.selected($data))">
                                    <td>
                                        <a
                                                class="btn btn-default contrib-button"
                                                data-bind="click:$root.add"
                                                rel="tooltip"
                                                title="Add contributor"
                                            >+</a>
                                    </td>
                                    <td>
                                        <img data-bind="attr:{src:$data.gravatar}" />
                                    </td>
                                    <td data-bind="text:user"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="col-md-6">
                        <h3>Contributors to Add</h3>
                        <table>
                            <tbody data-bind="foreach:{data:selection, afterRender:addTips}">
                                <tr class="search-contributor-result">
                                    <td>
                                        <a
                                                class="btn btn-default contrib-button"
                                                data-bind="click:$root.remove"
                                                rel="tooltip"
                                                title="Remove contributor"
                                            >-</a>
                                    </td>
                                    <td>
                                        <img data-bind="attr:{src:$data.gravatar}" />
                                    </td>
                                    <td data-bind="text:user"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div><!-- end col-md -->
                </div>
            </div><!-- end modal-body -->
            <div class="modal-footer">
                <a href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>
                <span data-bind="if:selection().length">
                    <a class="btn btn-primary" data-bind="click:submit">Add</a>
                </span>
            </div><!-- end modal-footer-->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

