<%inherit file="project/project_base.mako"/>
<%def name="title()">Contributors</%def>

##<%def name="content()">

##<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

<% import json %>

<div id="manageContributors" class="col-md-8">

    % if len(contributors) > 5:
        ${buttonGroup()}
    % endif

    <table class="table" id="manageContributors">
        <thead>
            <th></th>
            <th>Gravatar</th>
            <th>Name</th>
            <th>Permissions</th>
        </thead>
        <tbody data-bind="sortable: {data: contributors, as: 'contributor', afterRender: setupEditable, options: {containment: '#manageContributors'}}">
            <tr>
                <td>
                    <a
                            class="btn btn-default contrib-button btn-mini"
                            data-bind="click: $root.remove"
                            rel="tooltip"
                            title="Remove contributor"
                        >-</a>
                </td>
                <td>
                    <img data-bind="attr: {src: contributor.gravatar_url}" />
                </td>
                <td>
                    <span data-bind="text: contributor.fullname"></span>
                </td>
##                <td>
##                    <span data-bind="text: contributor.contributions"></span>
##                </td>
                <td data-bind="if: registered">
                    <a href="#" class="permission-editable" data-type="select"></a>
                </td>
            </tr>
        </tbody>
    </table>

    ${buttonGroup()}

</div>

<script type="text/javascript">
    var contributors = ${json.dumps(contributors)};
</script>

##</%def>

<%def name="javascript()">
</%def>

<%def name="buttonGroup()">
    % if 'admin' in user['permissions']:
        <a class="add-contributor btn btn-default contrib-button" href="#addContributors" data-toggle="modal">
            Add Contributors
        </a>
        <a class="btn btn-default" data-bind="click: sort">
            Sort by Surname
            <i data-bind="css: sortClass"></i>
        </a>
        <a class="btn btn-danger contrib-button" data-bind="click: cancel">Discard Changes</a>
        <a class="btn btn-success contrib-button" data-bind="click: submit">Save Changes</a>
    % endif
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="/static/js/manage.js"></script>
    <script type="text/javascript">
##        (function($) {
            var manageElm = $('#manageContributors')[0];
            var contributorsViewModel = new Manage.ViewModel(contributors);
            ko.applyBindings(contributorsViewModel, manageElm);
##        })($);
    </script>
</%def>
