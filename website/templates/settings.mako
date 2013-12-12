<%inherit file="base.mako"/>
<%def name="title()">Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "include/subnav.mako", "replace": true}'></div>
<h2 class="page-header">Account Settings</h2>


<div class="row">
    <div class="col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">Merge Accounts</h3></div>
            <div class="panel-body">
                <a href="/user/merge/">Merge with duplicate account</a>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">Profile Information</h3></div>
            <div class="panel-body">
                <div class="col-md-6 col-md-offset-3" id="profile">
                    <form>
                        <%include file="metadata/metadata_1.html" />
                        <div style="font-weight: bold;">APA Citation Format</div>
                        <div data-bind="text:$root.citation_name"></div>
                        <hr />
                        <button id="profile-impute" class="btn btn-default">
                            Guess fields below
                        </button>
                        <button id="profile-submit" class="btn btn-success">
                            Submit
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>

##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "/api/v1/settings/keys/",
##        "replace": true,
##        "kwargs" : {
##            "route": "/settings/"}
##        }'></div>

<script type="text/javascript" src="/static/js/metadata_1.js"></script>
<script type="text/javascript" src="/static/vendor/nameparser/nameparser.js"></script>

<script type="text/javascript">

    $(document).ready(function() {

        var nameParser = new NameParse();

        // Set up view model
        profileViewModel = new MetaData.ViewModel(${schema});
        profileViewModel.updateIdx('add', true);

        // Hack: Create an invisible computed to listen on full name and
        // update name part fields accordingly
        profileViewModel._fullname = ko.computed(function() {
            var self = profileViewModel;
            var fullname = self.observedData['fullname'].value();
            var parsed = nameParser.parse(fullname);
            var firstSplit = parsed.firstName.split(' ');
            self.observedData['given_name'].value(firstSplit[0]);
            self.observedData['middle_names'].value(firstSplit.slice(1).join(' '));
            self.observedData['family_name'].value(parsed.lastName);
            self.observedData['suffix'].value(parsed.suffix);
        });

        // Create computed for sample citation
        profileViewModel.citation_name = ko.computed(function() {
            var self = profileViewModel;
            var citation_name = $.trim(self.observedData['family_name'].value());
            var given_names = $.trim(self.observedData['given_name'].value()) + ' ' +
                $.trim(self.observedData['middle_names'].value());
            given_names = $.trim(given_names);
            if (given_names) {
                var initials = given_names
                    .split(' ')
                    .map(function(name) {
                        return name[0] + '.';
                    }).join(' ');
                citation_name = citation_name + ', ' + initials;
            }
            var suffix = $.trim(self.observedData['suffix'].value());
            if (suffix) {
                citation_name = citation_name + ', ' + suffix;
            }
            return citation_name;
        });

        // Unserialize data from server
        profileViewModel.unserialize(${names});

        // Apply completed bindings
        ko.applyBindings(profileViewModel, $('#profile')[0]);

        $('#profile form').on('submit', function() {

            // Serialize responses
            var serialized = profileViewModel.serialize(),
                data = serialized.data,
                complete = serialized.complete;

            // Stop if incomplete
            if (!complete) {
                return false;
            }

            // POST data
            $.ajax({
                url: '/api/v1/settings/names/',
                type: 'POST',
                data: JSON.stringify(data),
                contentType: "application/json",
                dataType: 'json'
            }).done(function(response) {
                console.log('Success');
            }).fail(function() {
                console.log('Failure');
            });

            // Stop event propagation
            return false;

        });

    });

</script>

</%def>
