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
                <li><a href='#userProfile'>Profile Information</a></li>
                <li><a href="#selectAddons">Select Add-ons to Configure</a></li>
                % if addon_enabled_settings:
                    <li><a href="#configureAddons">Configure Add-ons</a></li>
                % endif
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
                                    <th>Style</th>
                                    <th>Citation Format</th>
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
                            know at <a href="mailto:feedback+citations@osf.io">
                            feedback+citations@osf.io</a>.
                        </div>
                        <br />
                        <button id="profile-submit" class="btn btn-success">
                            Submit
                        </button>
                        <div>
                            <br />
                            <div id="profile-message" style="display: none;"></div>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <div id="selectAddons" class="panel panel-default">
            <div class="panel-heading"><h3 class="panel-title">Select Add-ons</h3></div>
            <div class="panel-body">

                <form id="selectAddonsForm">

                    % for category in addon_categories:

                        <%
                            addons = [
                                addon
                                for addon in addons_available
                                if category in addon.categories
                            ]
                        %>

                        % if addons:
                            <h3>${category.capitalize()}</h3>
                            % for addon in addons:
                                <div>
                                    <label>
                                        <input
                                            type="checkbox"
                                            name="${addon.short_name}"
                                            ${'checked' if addon.short_name in addons_enabled else ''}
                                        />
                                        ${addon.full_name}
                                    </label>
                                </div>
                            % endfor
                        % endif

                    % endfor

                    <button id="settings-submit" class="btn btn-success">
                        Submit
                    </button>

                </form>

            </div>
        </div>

        % if addon_enabled_settings:

            <div id="configureAddons" class="panel panel-default">
                <div class="panel-heading"><h3 class="panel-title">Configure Add-ons</h3></div>
                <div class="panel-body">

                    % for name in addon_enabled_settings:

                        <div mod-meta='{
                                "tpl": "../addons/${name}/templates/${name}_user_settings.mako",
                                "uri": "${user_api_url}${name}/settings/"
                            }'></div>

                        % if not loop.last:
                            <hr />
                        % endif

                    % endfor

                </div>
            </div>

        % endif

    </div>

</div>

## TODO: Review and un-comment
##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "/api/v1/settings/keys/",
##        "replace": true,
##        "kwargs" : {
##            "route": "/settings/"}
##        }'></div>

<script type="text/javascript" src="/static/js/metadata_1.js"></script>

<script type="text/javascript">

    function getInitials(names) {
        return names
            .split(' ')
            .map(function(name) {
                return name[0].toUpperCase() + '.';
            })
            .filter(function(initial) {
                return initial.match(/^[a-z]/i);
            }).join(' ');
    }

    $(document).ready(function() {

        function getNames() {
            var names = {};
            $.each(profileViewModel.serialize().data, function(key, value) {
                names[key] = $.trim(value);
            });
            return names;
        }

        function getSuffix(suffix) {
            var suffixLower = suffix.toLowerCase();
            if ($.inArray(suffixLower, ['jr', 'sr']) != -1) {
                suffix = suffix + '.';
                suffix = suffix.charAt(0).toUpperCase() + suffix.slice(1);
            } else if ($.inArray(suffixLower, ['ii', 'iii', 'iv', 'v']) != -1) {
                suffix = suffix.toUpperCase();
            }
            return suffix;
        }

        // Set up view model
        var profileViewModel = new MetaData.ViewModel(${schema});
        profileViewModel.updateIdx('add', true);

        // Patch computed for APA citation
        profileViewModel.citation_apa = ko.computed(function() {
            var names = getNames();
            var citation_name = names['family_name'];
            var given_names = $.trim(names['given_name'] + ' ' + names['middle_names']);
            if (given_names) {
                citation_name = citation_name + ', ' + getInitials(given_names);
            }
            if (names['suffix']) {
                citation_name = citation_name + ', ' + getSuffix(names['suffix']);
            }
            return citation_name;
        });

        // Patch computed for MLA citation
        profileViewModel.citation_mla = ko.computed(function() {
            var names = getNames();
            var citation_name = names['family_name'];
            if (names['given_name']) {
                citation_name = citation_name + ', ' + names['given_name'];
                if (names['middle_names']) {
                    citation_name = citation_name + ' ' + getInitials(names['middle_names']);
                }
            }
            if (names['suffix']) {
                citation_name = citation_name + ', ' + getSuffix(names['suffix']);
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

            // POST data asynchronously
            $.ajax({
                type: 'POST',
                url: '/api/v1/settings/names/parse/',
                data: JSON.stringify({fullname: fullname}),
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    modelData.given_name.value(response.given_name);
                    modelData.middle_names.value(response.middle_names);
                    modelData.family_name.value(response.family_name);
                    modelData.suffix.value(response.suffix);
                }
            });

            // Don't submit the form
            return false;

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

            // POST data asynchronously
            $.ajax({
                type: 'POST',
                url: '/api/v1/settings/names/',
                data: JSON.stringify(data),
                contentType: 'application/json',
                dataType: 'json'
            }).done(function(response) {
                $('#profile-message').text('Names updated')
                    .removeClass('text-danger').addClass('text-success')
                    .fadeOut(100).fadeIn();
            }).fail(function() {
                $('#profile-message').text('Error: Names not updated')
                    .removeClass('text-success').addClass('text-danger')
                    .fadeOut(100).fadeIn();
            });

            // Don't resubmit the form
            return false;

        });

    });

    // Set up submission for addon selection form
    $('#selectAddonsForm').on('submit', function() {

        var formData = {};
        $('#selectAddonsForm').find('input').each(function(idx, elm) {
            var $elm = $(elm);
            formData[$elm.attr('name')] = $elm.is(':checked');
        });

        $.ajax({
            type: 'POST',
            url: '/api/v1/settings/addons/',
            data: JSON.stringify(formData),
            contentType: 'application/json',
            dataType: 'json',
            success: function() {
                window.location.reload();
            }
        });

        return false;

    });


</script>

</%def>
