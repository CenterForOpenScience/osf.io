% if node_is_registration:
    <span class="label label-important" style="font-size:1.1em;margin-bottom:30px;">This node is a registration of <a href="${node_registered_from_url}">this node</a>; the content of the node has been frozen and cannot be edited.</span>
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

<header class="jumbotron subhead" id="overview">
    <div class="row">
        <div class="btn-toolbar" style="float:right;">
            <div class="btn-group">
            %if not node_is_public:
                <button class='btn disabled'>Private</button>
                % if user_is_contributor:
                    <a class="btn" id="publicButton" data-target="${node_api_url}permissions/public/">Make public</a>
                % endif
            %else:
                % if user_is_contributor:
                    <a class="btn" id="privateButton" data-target="${node_api_url}permissions/private/">Make private</a>
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
            % if user_is_contributor and not node_is_registration:
            <li><a href="${node_url}settings/">Settings</a></li>
            %endif
        </ul>
    </div>
</header>

<div class="modal hide fade" id="addContributors">

    <div class="modal-header">
        <h3 data-bind="text:pageTitle"></h3>
    </div>

    <div class="modal-body">

        <!-- Whom to add -->

        <div data-bind="if:page()=='whom'">

            <!-- Find contributors -->
            <form>
                <div class="row-fluid">
                    <div class="span6">
                        <div>
                            <input data-bind="value:query" />
                            <button class="btn" data-bind="click:search">Search</button>
                        </div>
                    </div>
                    <div class="span6 offset2" data-bind="if:parentId">
                        <a data-bind="click:importFromParent, text:'List contributors from ' + parentTitle"></a>
                    </div>
                </div>
            </form>

            <hr />

            <!-- Choose which to add -->
            <div class="row-fluid">

                <div class="span6">
                    <div>
                        <span class="modal-subheader">Results</span>
                        <a data-bind="click:addAll">Add all</a>
                    </div>
                    <table>
                        <tbody data-bind="foreach:{data:results, afterRender:addTips}">
                            <tr data-bind="if:!($root.selected($data))">
                                <td style="padding-right: 10px;">
                                    <a
                                            class="btn btn-default contrib-button"
                                            data-bind="click:$root.add"
                                            rel="tooltip"
                                            title="Add contributor"
                                        >+</a>
                                </td>
                                <td>
                                    <img data-bind="attr:{src:gravatar}" />
                                </td>
                                <td data-bind="text:fullname"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div class="span6">
                    <div>
                        <span class="modal-subheader">Adding</span>
                        <a data-bind="click:removeAll">Remove all</a>
                    </div>
                    <table>
                        <tbody data-bind="foreach:{data:selection, afterRender:addTips}">
                            <tr>
                                <td style="padding-right: 10px;">
                                    <a
                                            class="btn btn-default contrib-button"
                                            data-bind="click:$root.remove"
                                            rel="tooltip"
                                            title="Remove contributor"
                                        >-</a>
                                </td>
                                <td>
                                    <img data-bind="attr:{src:gravatar}" />
                                </td>
                                <td data-bind="text:fullname"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>

            </div>

        </div>

        <div data-bind="if:page()=='which'">

            <div>
                Adding contributor(s)
                <span data-bind="text:addingSummary()"></span>
                to component
                <span data-bind="text:title"></span>.
            </div>

            <hr />

            <div style="margin-bottom:10px;">
                Would you like to add these contributor(s) to any children of
                the current component?
            </div>

            <div class="row-fluid">

                <div class="span6">
                    <input type="checkbox" checked disabled />
                    <span data-bind="text:title"></span> (current component)
                    <div data-bind="foreach:nodes">
                        <div data-bind="style:{'margin-left':margin}">
                            <input type="checkbox" data-bind="checked:$parent.nodesToChange, value:id" />
                            <span data-bind="text:title"></span>
                        </div>
                    </div>
                </div>

                <div class="span6">
                    <div>
                        <a data-bind="click:selectNodes, css:{disabled:cantSelectNodes()}">Select all</a>
                    </div>
                    <div>
                        <a data-bind="click:deselectNodes, css:{disabled:cantDeselectNodes()}">De-select all</a>
                    </div>
                </div>

            </div>

        </div>

    </div>

    <div class="modal-footer">

        <a href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>

        <span data-bind="if:selection().length && page() == 'whom'">
            <a class="btn btn-primary" data-bind="visible:nodes().length==0, click:submit">Submit</a>
            <a class="btn" data-bind="visible:nodes().length, click:selectWhich">Next</a>
        </span>

        <span data-bind="if:page() == 'which'">
            <a class="btn" data-bind="click:selectWhom">Back</a>
            <a class="btn btn-primary" data-bind="click:submit">Submit</a>
        </span>

    </div>

</div>

<script src="//cdnjs.cloudflare.com/ajax/libs/knockout/2.3.0/knockout-min.js"></script>

## todo: move to static
<script>

    function attrMap(list, attr) {
        return $.map(list, function(item) {
            return item[attr];
        });
    }

    NODE_OFFSET = 25;

    var addContributorModel = function(title, parentId, parentTitle) {

        var self = this;

        self.title = title;
        self.parentId = parentId;
        self.parentTitle = parentTitle;

        self.page = ko.observable('whom');
        self.pageTitle = ko.computed(function() {
            return {
                whom: 'Add contributors',
                which: 'Select components'
            }[self.page()];
        });

        self.query = ko.observable();
        self.results = ko.observableArray();
        self.selection = ko.observableArray();

        self.nodes = ko.observableArray([]);
        self.nodesToChange = ko.observableArray();
        $.getJSON(
            nodeToUseUrl() + '/get_editable_children/',
            {},
            function(result) {
                $.each(result['children'], function(idx, child) {
                    child['margin'] = NODE_OFFSET + child['indent'] * NODE_OFFSET + 'px';
                });
                self.nodes(result['children']);
            }
        );

        self.selectWhom = function() {
            self.page('whom');
        };
        self.selectWhich = function() {
            self.page('which');
        };

        self.search = function() {
            $.getJSON(
                '/api/v1/user/search/',
                {query: self.query()},
                function(result) {
                    self.results(result['users']);
                }
            )
        };

        self.importFromParent = function() {
            $.getJSON(
                nodeToUseUrl() + '/get_contributors_from_parent/',
                {},
                function(result) {
                    self.results(result['contributors']);
                }
            )
        };

        self.addTips = function(elements) {
            elements.forEach(function(element) {
                $(element).find('.contrib-button').tooltip();
            });
        };

        self.add = function(data) {
            self.selection.push(data);
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.remove = function(data) {
            self.selection.splice(
                self.selection.indexOf(data), 1
            );
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.addAll = function() {
            $.each(self.results(), function(idx, result) {
                if (!(result in self.selection())) {
                    self.add(result);
                }
            });
        };

        self.removeAll = function() {
            $.each(self.selection(), function(idx, selected) {
                self.remove(selected);
            });
        };

        self.cantSelectNodes = function() {
            return self.nodesToChange().length == self.nodes().length;
        };
        self.cantDeselectNodes = function() {
            return self.nodesToChange().length == 0;
        };

        self.selectNodes = function() {
            self.nodesToChange(attrMap(self.nodes(), 'id'));
        };
        self.deselectNodes = function() {
            self.nodesToChange([]);
        };

        self.selected = function(data) {
            for (var idx=0; idx < self.selection().length; idx++) {
                if (data.id == self.selection()[idx].id)
                    return true;
            }
            return false;
        };

        self.addingSummary = ko.computed(function() {
            var names = $.map(self.selection(), function(result) {
                return result.fullname
            });
            return names.join(', ');
        });

        self.submit = function() {
            var user_ids = attrMap(self.selection(), 'id');
            $.ajax(
                nodeToUseUrl() + '/addcontributors/',
                {
                    type: 'post',
                    data: JSON.stringify({
                        user_ids: user_ids,
                        node_ids: self.nodesToChange()
                    }),
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
            self.page('whom');
            self.query('');
            self.results([]);
            self.selection([]);
            self.nodesToChange([]);
        };

    };

    var $addContributors = $('#addContributors');

    viewModel = new addContributorModel('${node_title}', '${parent_id}', '${parent_title}');
    ko.applyBindings(viewModel, $addContributors[0]);

    // Clear user search modal when dismissed; catches dismiss by escape key
    // or cancel button.
    $addContributors.on('hidden', function() {
        viewModel.clear();
    });

</script>
