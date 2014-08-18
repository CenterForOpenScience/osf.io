<%inherit file="project/project_base.mako" />

<%def name="title()">${node['title']}</%def>
<div id="application">
    <div class="row">
        <div class="col-md-12">
            <div class="input-group">
                <input type="text" class="form-control" placeholder="Search" data-bind="value: query">
                <span class="input-group-btn">
                    <button class="btn btn-default" data-bind="click: search"><i class="icon-search"></i></button>
                </span>
            </div>
        </div>
    </div>
    <br/>
    <div class="row">
        <div class="col-md-6">
            <table class="table table-hover">
                <thead>
                    <tr>
                    </tr>
                </thead>
                <tbody data-bind="foreach: results">
                    <tr data-bind="click: $parent.setSelected($data)">
                        <td>{{guid}}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="col-md-6">
            {{chosen | json:4}}
            <br/>
            <!-- {{metadata | json:4}} -->
            <table class="table">
                <tbody data-bind="foreach: metadata">
                    <tr>
                        <td>{{key}}</td>
                        <td>{{value}}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
    } else {
        global.ApplicationView  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    // Enable knockout punches
    ko.punches.enableAll();

    var ViewModel = function(url) {
        var self = this;
        self.url = url;
        self.query = ko.observable('');
        self.chosen = ko.observable();
        self.results = ko.observableArray([]);
        self.metadata = ko.observableArray([]);


        self.search = function() {
            $.ajax({
                url: self.url + '?q=' + self.query(),
                type: 'GET',
                success: self.searchRecieved
            });
        };

        self.getMetadata = function(id) {
            $.ajax({
                url: self.url + id,
                type: 'GET',
                success: self.metadataRecieved
            });
        }

        self.searchRecieved = function(data) {
            self.results(data.results);
        };

        self.metadataRecieved = function(data) {
            self.metadata(ko.utils.arrayMap(Object.keys(data), function(key) {
                return {
                    'key': key,
                    'value': data[key]
                }
            }));
        };

        self.setSelected = function(datum) {
            self.chosen(datum);
            self.getMetadata(datum.guid)
        };

    };

    function ApplicationView(selector, url) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
    }

    return ApplicationView

}));

    ApplicationView('#application', '${api_url_for('query_app', pid=node['id'])}');

</script>
