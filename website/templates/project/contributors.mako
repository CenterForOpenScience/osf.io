<%inherit file="project/project_base.mako"/>
<%def name="title()">Contributors</%def>

<% import json %>

<div id="manageContributors" class="col-md-12" style="display: none;">

<h2>Contributors</h2>

    <!-- ko if: userIsAdmin -->

    <table class="table">
        <thead>
            <th>Name</th>
            <th>
                Permissions
                <i class="icon-question-sign permission-info"
                        data-toggle="popover"
                        data-title="Permission Information"
                        data-container="body"
                        data-html="true"
                    ></i>
            </th>
            <th></th>
        </thead>
        <tr>
            <td>
                <a href="#addContributors" data-toggle="modal">
                    Click to add a contributor
                </a>
            </td>
        </tr>
        <tbody data-bind="sortable: {data: contributors, as: 'contributor', afterRender: setupEditable, options: {containment: '#manageContributors'}}">
            <tr data-bind="click: unremove, css: {'contributor-delete-staged': deleteStaged}">
                <td>
                    <img data-bind="attr: {src: contributor.gravatar_url}" />
                    <span data-bind="text: contributor.fullname"></span>
                </td>
                <td>
                    <span data-bind="visible: notDeleteStaged">
                        <a href="#" class="permission-editable" data-type="select"></a>
                    </span>
                    <span data-bind="visible: deleteStaged">
                        <span data-bind="text: formatPermission"></span>
                    </span>
                </td>
                <td>
                    <!-- ko ifnot: deleteStaged -->
                        <a
                                class="btn btn-danger contrib-button btn-mini"
                                data-bind="click: remove"
                                rel="tooltip"
                                title="Remove contributor"
                            >-</a>
                    <!-- /ko -->
                    <!-- ko if: deleteStaged -->
                        Removed
                    <!-- /ko -->
                </td>
            </tr>
        </tbody>
    </table>

    ${buttonGroup()}

    <!-- /ko -->
    <!-- ko ifnot: userIsAdmin -->

    <table class="table">
        <thead>
            <th>Name</th>
            <th>
                Permissions
                <i class="icon-question-sign permission-info"
                        data-toggle="popover"
                        data-title="Permission Information"
                        data-container="body"
                        data-html="true"
                    ></i>
            </th>
            <th></th>
        </thead>
        <tbody data-bind="foreach: {data: contributors, as: 'contributor', afterRender: setupEditable, options: {containment: '#manageContributors'}}">
            <tr data-bind="click: unremove, css: {'contributor-delete-staged': deleteStaged}">
                <td>
                    <img data-bind="attr: {src: contributor.gravatar_url}" />
                    <span data-bind="text: contributor.fullname"></span>
                </td>
                <td>
                    <span data-bind="text: formatPermission"></span>
                </td>
                <td>
                <!-- ko if: contributorIsUser -->
                    <!-- ko ifnot: deleteStaged -->
                        <a
                                class="btn btn-danger contrib-button btn-mini"
                                data-bind="click: remove"
                                rel="tooltip"
                                title="Remove contributor"
                            >-</a>
                    <!-- /ko -->
                    <!-- ko if: deleteStaged -->
                        Removed
                    <!-- /ko -->
                <!-- /ko -->
                </td>
            </tr>
        </tbody>
    </table>

    ${buttonGroup()}
    <!-- /ko -->

</div>

<script type="text/javascript">
    var contributors = ${json.dumps(contributors)};
    var user = ${json.dumps(user)}
</script>

<%def name="javascript()">
</%def>

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
    <script src="/static/js/manage.js"></script>
    <script type="text/javascript">
        (function($) {
            var $manageElm = $('#manageContributors');
            var contributorsViewModel = new Manage.ViewModel(contributors, user);
            ko.applyBindings(contributorsViewModel, $manageElm[0]);
            $manageElm.show();
        })($);
    </script>
</%def>
