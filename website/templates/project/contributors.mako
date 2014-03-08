<%inherit file="project/project_base.mako"/>
<%def name="title()">Contributors</%def>

<% import json %>

<div id="manageContributors" class="col-md-12" style="display: none;">

<h2>Contributors</h2>

    ##% if len(contributors) > 5:
      ##  ${buttonGroup()}
    ##% endif

    <table class="table">
        <thead>
            <th></th>
            <th>Name</th>
            <th>Permissions</th>
        </thead>
        <tr>
            <td>
                <a class="btn btn-default btn-mini add-contributor contrib-button" href="#addContributors" data-toggle="modal">
                    +
                </a>
            </td>
            <td>
                Click to the left to add a contributor
            </td>
        </tr>
        <tbody data-bind="sortable: {data: contributors, as: 'contributor', afterRender: setupEditable, options: {containment: '#manageContributors'}}">
            <tr>
                <td>
                    <a
                            class="btn btn-danger contrib-button btn-mini"
                            data-bind="click: $root.remove"
                            rel="tooltip"
                            title="Remove contributor"
                        >-</a>
                </td>
                <td>
                    <img data-bind="attr: {src: contributor.gravatar_url}" />
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
            var contributorsViewModel = new Manage.ViewModel(contributors);
            ko.applyBindings(contributorsViewModel, $manageElm[0]);
            $manageElm.show();
        })($);
    </script>
</%def>
