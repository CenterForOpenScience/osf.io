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
                        </tr>
                    </thead>
                    <tbody data-bind="foreach: keys">
                        <tr>
                            <td>{{label | default:"No Label"}}</td>
                            <td>{{key}}</td>
                            <td><a data-bind="click: $parent.deleteKey.bind(key)"><i class="icon-remove text-danger"></i></a></td>
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

<script type="text/javascript">

    ;(function (global, factory) {
        if (typeof define === 'function' && define.amd) {
            define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
        } else {
            global.ApiKeyView  = factory(ko, jQuery);
        }
    }(this, function(ko, $) {
        // Enable knockout punches
        ko.punches.enableAll();

        var ViewModel = function(url) {
            var self = this;
            self.url = url;
            self.keys = ko.observableArray([]);
            self.label = ko.observable('');

            self.keysRecieved = function(data) {
                self.keys(data.keys);
            }

            self.createKey = function() {
                $.osf.postJSON(self.url, {label: self.label()});
            }

            self.deleteKey = function(key) {
                bootbox.confirm('Are you sure you want to delete this API key?', function(result) {

                });
            }

            function fetch() {
                $.ajax({
                    url: self.url,
                    type: 'GET',
                    success: self.keysRecieved
                });
            }

            fetch();

        };

        function ApiKeyView(selector, url) {
            // Initialization code
            var self = this;
            self.viewModel = new ViewModel(url);
            window.model = self.viewModel;
            $.osf.applyBindings(self.viewModel, selector);
        }

        return ApiKeyView

    }));

    ApiKeyView('#apiKey', '${api_url_for('get_keys')}');

</script>
</%def>
