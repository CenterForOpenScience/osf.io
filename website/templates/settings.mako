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

        <div id="userProfile">

            <ul class="nav nav-tabs">
                <li class="active"><a href="#names" data-toggle="tab">Name</a></li>
                <li><a href="#social" data-toggle="tab">Social</a></li>
                <li><a href="#jobs" data-toggle="tab">Employment</a></li>
                <li><a href="#schools" data-toggle="tab">Education</a></li>
            </ul>

            <div class="tab-content">

                <div class="tab-pane active" id="names">

                    <form role="form" data-bind="submit: submit">

                        <h3>Name</h3>

                        <div class="form-group">
                            <label>Full Name (e.g. Rosalind Elsie Franklin)</label>
                            <input class="form-control" data-bind="value: full" />
                        </div>

                        <div>
                            <a class="btn btn-default" data-bind="enabled: hasFirst(), click: impute">Guess names</a>
                        </div>

                        <div class="form-group">
                            <label>Given Name (e.g. Rosalind)</label>
                            <input class="form-control" data-bind="value: given" />
                        </div>

                        <div class="form-group">
                            <label>Middle Name(s) (e.g. Elsie)</label>
                            <input class="form-control" data-bind="value: middle" />
                        </div>

                        <div class="form-group">
                            <label>Family Name (e.g. Franklin)</label>
                            <input class="form-control" data-bind="value: family" />
                        </div>

                        <div class="form-group">
                            <label>Suffix</label>
                            <input class="form-control" data-bind="value: suffix" />
                        </div>

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
                                    <td>{{ citeApa }}</td>
                                </tr>
                                <tr>
                                    <td>MLA</td>
                                    <td>{{ citeMla }}</td>
                                </tr>
                            </tbody>
                        </table>

                        <button
                                type="submit"
                                class="btn btn-success"
                                data-bind="enable: isValid"
                            >Submit</button>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr.class: messageClass"></p>
                        </div>

                    </form>

                </div>

                <div class="tab-pane" id="social">

                    <form role="form" data-bind="submit: submit">

                        <h3>Social</h3>

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

                        <button
                                type="submit"
                                class="btn btn-success"
                                data-bind="enable: isValid"
                            >Submit</button>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr.class: messageClass"></p>
                        </div>

                    </form>

                </div>

                <div class="tab-pane" id="jobs">

                    <form role="form" data-bind="submit: submit">

                        <h3>Education / Employment History</h3>

                        <div data-bind="foreach: contents">

                            <div>Position {{ $index() + 1 }}</div>

                            <div>
                                <div class="pull-right">
                                    <a class="btn btn-danger" data-bind="click: $parent.removeContent">Remove</a>
                                </div>
                            </div>

                            <div class="form-group">
                                <label>Institution / Employer</label>
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
                                <input class="form-control" data-bind="value: start" />
                            </div>

                            <div class="form-group">
                                <label>End Date</label>
                                <input class="form-control" data-bind="value: end" />
                            </div>

                            <hr data-bind="visible: $index() != ($parent.contents().length - 1)" />

                        </div>

                        <div>
                            <a class="btn btn-default" data-bind="click: addContent">
                                Add
                            </a>
                        </div>

                        <div class="padded">
                            <button
                                    type="submit"
                                    class="btn btn-success"
                                    data-bind="enable: isValid"
                                >Submit</button>
                        </div>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr.class: messageClass"></p>
                        </div>

                    </form>

                </div>

                <div class="tab-pane" id="schools">

                    <form role="form" data-bind="submit: submit">

                        <h3>Education</h3>

                        <div data-bind="foreach: contents">

                            <div>Position {{ $index() + 1 }}</div>

                            <div>
                                <div class="pull-right">
                                    <a class="btn btn-danger" data-bind="click: remove">Remove</a>
                                </div>
                            </div>

                            <div class="form-group">
                                <label>Institution</label>
                                <input class="form-control" data-bind="value: institution" />
                            </div>

                            <div class="form-group">
                                <label>Department</label>
                                <input class="form-control" data-bind="value: department" />
                            </div>

                            <div class="form-group">
                                <label>Degree</label>
                                <input class="form-control" data-bind="value: degree" />
                            </div>

                            <div class="form-group">
                                <label>Start Date</label>
                                <input class="form-control" data-bind="value: start" />
                            </div>

                            <div class="form-group">
                                <label>End Date</label>
                                <input class="form-control" data-bind="value: end" />
                            </div>

                            <hr data-bind="visible: $index() != ($parent.contents().length - 1)" />

                        </div>

                        <div>
                            <a class="btn btn-default" data-bind="click: addContent">
                                Add
                            </a>
                        </div>

                        <div class="padded">
                            <button
                                    type="submit"
                                    class="btn btn-success"
                                    data-bind="enable: isValid"
                                >Submit</button>
                        </div>

                        <!-- Flashed Messages -->
                        <div class="help-block">
                            <p data-bind="html: message, attr.class: messageClass"></p>
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
        var nameUrls = {
            crud: '${ api_url_for('serialize_names') }',
            impute: '${ api_url_for('impute_names') }'
        };
        var socialUrls = {
            crud: '${ api_url_for('serialize_social') }'
        };
        var jobsUrls = {
            crud: '${ api_url_for('serialize_jobs') }'
        };
        var schoolsUrls = {
            crud: '${ api_url_for('serialize_schools') }'
        };
        var names = new profile.Names('#names', nameUrls);
        var social = new profile.Social('#social', socialUrls);
        var jobs = new profile.Jobs('#jobs', jobsUrls);
        var schools = new profile.Schools('#schools', schoolsUrls);
    });

</script>


</%def>
