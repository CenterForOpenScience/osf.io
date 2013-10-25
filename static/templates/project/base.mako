## todo: move to warnings.py
<%
    make_public_warning = 'Once a project is made public, there is no way to guarantee that access to the data it contains can be complete prevented. Users should assume that once a project is made public, it will always be public. Are you absolutely sure you would like to continue?'
    make_private_warning = 'Making a project will prevent users from viewing it on this site, but will have no impact on external sites, including Google\'s cache. Would you like to continue?'
%>

% if node_is_registration:
    <span class="label label-important" style="font-size:1.1em;margin-bottom:30px;">This node is a registration of <a href="${node_registered_from_url}">this node</a>; the content of the node has been frozen and cannot be edited.</span>
    <style type="text/css">
    .watermarked {
        background-image:url('/static/read-only.png');
        background-repeat:repeat;
    }
    </style>
% endif

<header class="jumbotron subhead" id="overview">

    <div class="row">

        <div class="btn-toolbar" style="float:right;">

            <div class="btn-group">
            %if not node_is_public:
                <button class='btn disabled'>Private</button>
                % if user_is_contributor:
                    <a class="btn" href="${node_url}permissions/public/" data-confirm="${make_public_warning}">Make public</a>
                % endif
            %else:
                % if user_is_contributor:
                    <a class="btn" href="${node_url}permissions/private/" data-confirm="${make_private_warning}">Make private</a>
                % endif
                <button class="btn disabled">Public</button>
            %endif
            </div>

            <div class="btn-group">
                % if user_name:
                    <a rel="tooltip" title="Watch" class="btn" href="#" onclick="NodeActions.toggleWatch()">
                % else:
                    <a rel="tooltip" title="Watch" class="btn disabled" href="#">
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
                        class="btn node-fork-btn"
                        onclick="NodeActions.forkNode();"
                    % else:
                        class="btn disabled node-fork-btn"
                    % endif
                >
                    <i class="icon-fork"></i>&nbsp;${node_fork_count}
                </a>

            </div>

        </div>

        %if user_can_edit:
            <script>
                $(function() {
                    function urlDecode(str) {
                        return decodeURIComponent((str+'').replace(/\+/g, '%20'));
                    }

                    $('#node-title-editable').editable({
                       type:  'text',
                       pk:    '${node_id}',
                       name:  'title',
                       url:   '${node_api_url}edit/',
                       title: 'Edit Title',
                       placement: 'bottom',
                       value: '${ '\\\''.join(node_title.split('\'')) }',
                       success: function(data){
                            document.location.reload(true);
                       }
                    });
                });
            </script>
        %endif

        <div class="span4">

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

    <div class="subnav">
        <ul class="nav nav-pills">
            <li><a href="${node_url}">Dashboard</a></li>
            <li><a href="${node_url}wiki/">Wiki</a></li>
            <li><a href="${node_url}statistics/">Statistics</a></li>
            <li><a href="${node_url}files/">Files</a></li>
            <li><a href="${node_url}registrations/">Registrations</a></li>
            <li><a href="${node_url}forks/">Forks</a></li>
            % if user_is_contributor:
            <li><a href="${node_url}settings/">Settings</a></li>
            %endif
        </ul>
    </div>
</header>

<script src="//cdnjs.cloudflare.com/ajax/libs/knockout/2.3.0/knockout-min.js"></script>

<div class="modal hide fade" id="addContributors">

    <div class="modal-header">
        <h3>Add Contributors</h3>
    </div>

    <div class="modal-body">

        <!-- Search box -->
        <form class="form-inline">
            <input data-bind="value:query" />
            <button class="btn" data-bind="click:search">Search</button>
        </form>

        <hr />

        <div class="row-fluid">

            <div class="span6">
                <h3>Search Results</h3>
                <table>
                    <tbody data-bind="foreach:results">
                        <tr data-bind="if:!($root.selected($data))">
                            <td style="padding-right: 10px;">
                                <a class="btn" data-bind="click:$root.add">+</a>
                            </td>
                            <td>
                                <img data-bind="attr:{src:$data.gravatar}" />
                            </td>
                            <td data-bind="text:user"></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="span6">
                <h3>Contributors to Add</h3>
                <table>
                    <tbody data-bind="foreach:selection">
                        <tr>
                            <td style="padding-right: 10px;">
                                <a class="btn" data-bind="click:$root.remove">x</a>
                            </td>
                            <td>
                                <img data-bind="attr:{src:$data.gravatar}" />
                            </td>
                            <td data-bind="text:user"></td>
                        </tr>
                    </tbody>
                </table>
            </div>

        </div>

    </div>

    <div class="modal-footer">
        <span data-bind="if:selection().length">
            <a class="btn" data-bind="click:submit">Add</a>
        </span>
        <a href="#" class="btn" data-dismiss="modal">Cancel</a>
    </div>

</div>

<script type="text/javascript">

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

        self.add = function(data) {
            self.selection.push(data);
        };

        self.remove = function(data) {
            self.selection.splice(
                self.selection.indexOf(data), 1
            );
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
            $.post(
                '${node_api_url}addcontributors/',
                {user_ids: JSON.stringify(user_ids)},
                function(response) {
                    if (response.status === 'success') {
                        window.location.reload();
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

    viewModel = new addContributorModel();
    ko.applyBindings(viewModel, $('#addContributors')[0]);

    /*
     * Clear user search modal when dismissed; catches dismiss by escape key
     * or cancel button.
     */
    $('#addContributors').on('hidden', function() {
        viewModel.clear();
    });

</script>