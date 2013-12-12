<%inherit file="base.mako"/>
<%def name="title()">Settings</%def>
<%def name="content()">
<div mod-meta='{"tpl": "include/subnav.mako", "replace": true}'></div>
<h2 class="page-header">Account Settings</h2>

## TODO: Review and un-comment
##<div class="row">
##    <div class="col-md-6">
##        <div class="panel panel-default">
##            <div class="panel-heading"><h3 class="panel-title">Merge Accounts</h3></div>
##            <div class="panel-body">
##                <a href="/user/merge/">Merge with duplicate account</a>
##            </div>
##        </div>
##    </div>
##</div>

<div class="row">
    <div class="col-md-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href='#userProfile'>User Profile</a></li>
            </ul>
        </div><!-- end sidebar -->
    </div>
    <div class="col-md-6">
        <div id="userProfile" class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">Profile Information</h3></div>
            <div class="panel-body">
                <div id="profile">
                    <form>
                        <%include file="metadata/metadata_1.html" />
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Format</th>
                                    <th>Citation</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>APA</td>
                                    <td data-bind="text:$root.citation_apa"></td>
                                </tr>
                                <tr>
                                    <td>MLA</td>
                                    <td data-bind="text:$root.citation_mla"></td>
                                </tr>
                            </tbody>
                        </table>
                        <div>
                            If you have any questions or comments about how
                            your name will appear in citations, please let us
                            know at <a href="mailto:feedback@osf.io">
                            feedback@osf.io</a>.
                        </div>
                        <br />
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

<script type="text/javascript">

    function getNames() {
        var names = {};
        $.each(profileViewModel.serialize().data, function(key, value) {
            names[key] = $.trim(value);
        });
        return names;
    }

    $(document).ready(function() {

        // Set up view model
        profileViewModel = new MetaData.ViewModel(${schema});
        profileViewModel.updateIdx('add', true);

        // Create computed for sample citation
        profileViewModel.citation_apa = ko.computed(function() {
            var names = getNames();
            var citation_name = names['family_name'];
            var given_names = $.trim(names['given_name'] + names['middle_names']);
            if (given_names) {
                var initials = given_names
                    .split(' ')
                    .map(function(name) {
                        return name[0] + '.';
                    }).join(' ');
                citation_name = citation_name + ', ' + initials;
            }
            if (names['suffix']) {
                citation_name = citation_name + ', ' + names['suffix'];
            }
            return citation_name;
        });

        // Create computed for sample citation
        profileViewModel.citation_mla = ko.computed(function() {
            var names = getNames();
            var citation_name = names['family_name'];
            if (names['given_name']) {
                citation_name = citation_name + ', ' + names['given_name'];
                if (names['middle_names']) {
                    var initials = names['middle_names'].split(' ')
                        .map(function(name) {
                            return name[0] + '.';
                        }).join(' ');
                    citation_name = citation_name + ' ' + initials;
                }
            }
            if (names['suffix']) {
                citation_name = citation_name + ', ' + names['suffix'];
            }
            return citation_name;
        });

        // Unserialize data from server
        profileViewModel.unserialize(${names});

        // Apply completed bindings
        ko.applyBindings(profileViewModel, $('#profile')[0]);

        $('#profile form').delegate('#profile-impute', 'click', function() {
            var modelData = profileViewModel.observedData;
            var fullname = modelData['fullname'].value();
            $.ajax({
                url: '/api/v1/settings/names/parse/',
                type: 'POST',
                data: JSON.stringify({fullname: fullname}),
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    modelData['given_name'].value(response['given_name']);
                    modelData['middle_names'].value(response['middle_names']);
                    modelData['family_name'].value(response['family_name']);
                    modelData['suffix'].value(response['suffix']);
                }
            });
        });

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
                contentType: 'application/json',
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
