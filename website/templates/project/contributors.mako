<%inherit file="project/project_base.mako"/>
<%def name="title()">Contributors</%def>

<div class="row">
    <div class="col-md-12">

    <h2>Contributors</h2>
        <div id="manageContributors" style="display: none;">
                <table id="manageContributorsTable" class="table">
                    <thead>
                        <tr>
                        <th class="col-sm-6">Name</th>
                        <th class="col-sm-5">
                            Permissions
                            <i class="icon-question-sign permission-info"
                                    data-toggle="popover"
                                    data-title="Permission Information"
                                    data-container="body"
                                    data-html="true"
                                ></i>
                        </th>
                        <th class="col-sm-1"></th>
                        </tr>
                    </thead>
                    <tr data-bind="if: userIsAdmin">
                        <td colspan="3">
                            <a href="#addContributors" data-toggle="modal">
                                Click to add a contributor
                            </a>
                        </td>
                    </tr>
                    <tbody data-bind="sortable: {template: 'contribTpl',
                        data: contributors, as: 'contributor',
                        isEnabled: userIsAdmin,
                        afterRender: setupEditable,
                        options: {containment: '#manageContributors'}}">
                    </tbody>
                </table>
                ${buttonGroup()}
        </div>
    % if 'write' in user['permissions']:
        <h2>Private Links</h2>
            <div id="linkScope" >
                    <table id="privateLinkTable" class="table">
                        <thead>
                            <tr>
                            <th class="col-sm-2 link-name">Private Link</th>
                            <th class="col-sm-4 link-label">Label
                            </th>
                            <th class="col-sm-3 link-date">Created Date</th>
                            <th class="col-sm-2 link-creator">Created By</th>
                            <th class="col-sm-1"></th>
                            </tr>
                        </thead>
                        <tr >
                            <td colspan="3">
                                <a href="#private-link" data-toggle="modal">
                                    Click to generate a private link
                                </a>
                            </td>
                        </tr>
                        <tbody >
                            % for link in node['private_links']:
                                <tr>
                                <td class="col-sm-4 link-name">
                                    <button class="btn btn-default btn-mini copy-button" data-trigger="manual" rel="tooltip" title="Click to copy" data-clipboard-text="${node['absolute_url']}?key=${link['key']}" >
                                        <span class="icon-copy" ></span>
                                    </button>
                                    <a class="key-name" >${node['absolute_url']}?key=${link['key']}</a>
                                </td>
                                <td class="col-sm-2 link-label">${link['label'] if link['label'] else "None"}</td>
                                <td class="col-sm-3 link-date">
                                    <span class="link-create-date">${link['date_created']}</span>
                                </td>
                                <td class="col-sm-2 link-creator">${link['creator']}</td>
                                <td class="col-sm-1">
                                    <a class="remove-private-link btn btn-danger btn-mini" rel="tooltip" title="Remove private link" data-link="${link['id']}">-</a>
                                </td>
                                </tr>
                            % endfor
                        </tbody>
                    </table>

            </div>
    % endif

    </div><!-- end col-md -->
</div><!-- end row -->


<script id="contribTpl" type="text/html">
    <tr data-bind="click: unremove, css: {'contributor-delete-staged': deleteStaged}">
        <td>
            <img data-bind="attr: {src: contributor.gravatar_url}" />
            <span data-bind="text: contributor.fullname"></span>
        </td>
        <td>
            <!-- ko if: $parent.userIsAdmin -->
                <span data-bind="visible: notDeleteStaged">
                    <a href="#" class="permission-editable" data-type="select"></a>
                </span>
                <span data-bind="visible: deleteStaged">
                    <span data-bind="text: formatPermission"></span>
                </span>
            <!-- /ko -->
            <!-- ko ifnot: $parent.userIsAdmin -->
                <span data-bind="text: formatPermission"></span>
            <!-- /ko -->
        </td>
        <td>
            <!-- ko if: $parent.userIsAdmin -->
                <!-- ko ifnot: deleteStaged -->
                    <a
                            class="btn btn-danger contrib-button btn-mini"
                            data-bind="click: remove"
                            rel="tooltip"
                            title="Remove contributor"
                        >–</a>
                <!-- /ko -->
                <!-- ko if: deleteStaged -->
                    Removed
                <!-- /ko -->
            <!-- /ko -->
            <!-- ko ifnot: $parent.userIsAdmin -->
                <!-- ko if: contributorIsUser -->
                    <a
                            class="btn btn-danger contrib-button btn-mini"
                            data-bind="click: removeSelf"
                            rel="tooltip"
                            title="Remove contributor"
                        >-</a>
                    <!-- /ko -->
            <!-- /ko -->
        </td>
    </tr>
</script>


<%def name="buttonGroup()">
    % if 'admin' in user['permissions']:
        <a class="btn btn-danger contrib-button" data-bind="click: cancel, visible: changed">Discard Changes</a>
        <a class="btn btn-success contrib-button" data-bind="click: submit, visible: canSubmit">Save Changes</a>
        <br /><br />
        <div data-bind="text: messageText, css: messageClass"></div>
    % endif
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <% import json %>
    <script src="/static/js/contribManager.js"></script>
    <script src="/static/vendor/zeroclipboard/ZeroClipboard.min.js"></script>
    <script src="/static/vendor/zeroclipboard/main.js"></script>
    <script type="text/javascript">
        (function() {
            var contributors = ${json.dumps(contributors)};
            var user = ${json.dumps(user)};
            var manager = new ContribManager('#manageContributors', contributors, user);

            $('tbody .link-create-date').each(function(idx, elem) {
                var e = $(elem);
                var dt = new $.osf.FormattableDate(e.text());
                e.text(dt.local);
                e.tooltip({
                    title: dt.utc,
                    container: "body"
                });
            })
        })();
    </script>
</%def>
