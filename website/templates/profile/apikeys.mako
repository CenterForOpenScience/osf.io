<%inherit file="base.mako"/>
<%def name="title()">Configure API keys</%def>
<%def name="content()">
<h2 class="page-header">Configure API keys</h2>

<div class="row">

    <div class="col-md-3">

        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                <li><a href="#">Configure API Keys</a></li>
            </ul>
        </div><!-- end sidebar -->

    </div>

    <div class="col-md-6">

        <div id="apiKey" class="panel panel-default scripted">
            <div class="panel-heading"><h3 class="panel-title">Manage API Keys</h3></div>
            <div class="panel-body">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Label</th>
                            <th>Key</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody data-bind="foreach: keys">
                        <tr>
                            <td>{{label | default:"No Label"}}</td>
                            <td>{{key}}</td>
                            <td><a data-bind="click: $parent.deleteKey.bind()"><i class="icon-remove text-danger"></i></a></td>
                        </tr>
                    </tbody>
                </table>
                <hr />
                 <form class="input-group" data-bind="submit: createKey">
                    <input type="text" class="form-control" placeholder="Label" data-bind="value: label">
                    <span class="input-group-btn">
                        <button class="btn btn-default">Create New Key</button>
                    </span>
                </form>
            </div>
        </div>
    </div>

</div>


</%def>

<%def name="javascript_bottom()">
  <script src=${"/static/public/js/apikey-page.js" | webpack_asset}></script>
  ${parent.javascript_bottom()}
</%def>

