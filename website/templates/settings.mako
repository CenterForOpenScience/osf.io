<%inherit file="base.mako"/>
<%def name="title()">Settings</%def>
<%def name="content()">
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

                    <form role="form" data-bind="submit: submit">

                        <!--  -->
                        <div data-bind="with: names">

                            <div class="form-group">
                                <label>Full Name</label>
                                <input class="form-control" data-bind="value: full" />
                            </div>

                            <div class="form-group">
                                <label>Given Name</label>
                                <input class="form-control" data-bind="value: given" />
                            </div>

                            <div class="form-group">
                                <label>Middle Name(s)</label>
                                <input class="form-control" data-bind="value: middle" />
                            </div>

                            <div class="form-group">
                                <label>Family Name</label>
                                <input class="form-control" data-bind="value: family" />
                            </div>

                            <div class="form-group">
                                <label>Suffix</label>
                                <input class="form-control" data-bind="value: suffix" />
                            </div>

                        </div>

                        <!--  -->
                        <div data-bind="with: social">

                            <div class="form-group">
                                <label>Personal Site</label>
                                <input class="form-control" data-bind="value: personal" />
                            </div>

                            <div class="form-group">
                                <label>ORCID</label>
                                <input class="form-control" data-bind="value: orcid" />
                            </div>

                            <div class="form-group">
                                <label>ResearcherID</label>
                                <input class="form-control" data-bind="value: researcherId" />
                            </div>

                            <div class="form-group">
                                <label>Twitter</label>
                                <input class="form-control" data-bind="value: twitter" />
                            </div>

                        </div>

                        <!--  -->
                        <div>

                            <div data-bind="foreach: history">

                                <div>

                                    <div class="form-group">
                                        <label>Institution</label>
                                        <input class="form-control" data-bind="value: institution" />
                                    </div>

                                    <div class="form-group">
                                        <label>Department</label>
                                        <input class="form-control" data-bind="value: department" />
                                    </div>

                                    <div class="form-group">
                                        <label>Job Title</label>
                                        <input class="form-control" data-bind="value: title" />
                                    </div>

                                    <div class="form-group">
                                        <label>Start Date</label>
                                        <input class="form-control" data-bind="value: startDate" />
                                    </div>

                                    <div class="form-group">
                                        <label>End Date</label>
                                        <input class="form-control" data-bind="value: endDate" />
                                    </div>

                                </div>

                                <a class="btn btn-danger" data-bind="click: remove">Remove</a>

                            </div>

                            <a class="btn btn-default" data-bind="click: addHistory">Add</a>

                        </div>

                        <button type="submit" class="btn btn-success">Submit</button>

                    </form>

##                    <form>
##                        <%include file="metadata/metadata_1.html" />
##                        <table class="table">
##                            <thead>
##                                <tr>
##                                    <th>Style</th>
##                                    <th>Citation Format</th>
##                                </tr>
##                            </thead>
##                            <tbody>
##                                <tr>
##                                    <td>APA</td>
##                                    <td data-bind="text:$root.citation_apa"></td>
##                                </tr>
##                                <tr>
##                                    <td>MLA</td>
##                                    <td data-bind="text:$root.citation_mla"></td>
##                                </tr>
##                            </tbody>
##                        </table>
##                        <div>
##                            If you have any questions or comments about how
##                            your name will appear in citations, please let us
##                            know at <a href="mailto:feedback+citations@osf.io">
##                            feedback+citations@osf.io</a>.
##                        </div>
##                        <br />
##                        <button id="profile-submit" class="btn btn-success">
##                            Submit
##                        </button>
##                        <div>
##                            <br />
##                            <div id="profile-message" style="display: none;"></div>
##                        </div>
##                    </form>
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

<script type="text/javascript">

    // TODO: Move all this to its own module
    function formToObj(form) {
        var rv = {};
        $.each($(form).serializeArray(), function(_, value) {
            rv[value.name] = value.value;
        });
        return rv;
    }

    function on_submit_settings() {
        var $this = $(this),
            addon = $this.attr('data-addon'),
            owner = $this.find('span[data-owner]').attr('data-owner'),
            msgElm = $this.find('.addon-settings-message');

        var url = owner == 'user'
            ? '/api/v1/settings/' + addon + '/'
            : nodeApiUrl + addon + '/settings/';

        $.ajax({
            url: url,
            data: JSON.stringify(formToObj($this)),
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json'
        }).success(function() {
            msgElm.text('Settings updated')
                .removeClass('text-danger').addClass('text-success')
                .fadeOut(100).fadeIn();
        }).fail(function(xhr) {
            var message = 'Error: ';
            var response = JSON.parse(xhr.responseText);
            if (response && response.message) {
                message += response.message;
            } else {
                message += 'Settings not updated.'
            }
            msgElm.text(message)
                .removeClass('text-success').addClass('text-danger')
                .fadeOut(100).fadeIn();
        });

        return false;
    }

##    $(document).ready(function() {
##
##        // Patch computed for APA citation
##        profileViewModel.citation_apa = ko.computed(function() {
##            var names = getNames();
##            var citation_name = names['family_name'];
##            var given_names = $.trim(names['given_name'] + ' ' + names['middle_names']);
##            if (given_names) {
##                citation_name = citation_name + ', ' + getInitials(given_names);
##            }
##            if (names['suffix']) {
##                citation_name = citation_name + ', ' + getSuffix(names['suffix']);
##            }
##            return citation_name;
##        });
##
##        // Patch computed for MLA citation
##        profileViewModel.citation_mla = ko.computed(function() {
##            var names = getNames();
##            var citation_name = names['family_name'];
##            if (names['given_name']) {
##                citation_name = citation_name + ', ' + names['given_name'];
##                if (names['middle_names']) {
##                    citation_name = citation_name + ' ' + getInitials(names['middle_names']);
##                }
##            }
##            if (names['suffix']) {
##                citation_name = citation_name + ', ' + getSuffix(names['suffix']);
##            }
##            return citation_name;
##        });
##
##    });

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

    $script(['/static/js/profile.js']);
    $script.ready('profile', function() {
        var getUrl = '${ api_url_for('serialize_personal') }';
        var putUrl = '${ api_url_for('unserialize_personal') }';
        var profile = new Profile('#userProfile', getUrl, putUrl);
    });

</script>


</%def>
