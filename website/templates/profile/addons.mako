<%inherit file="base.mako"/>
<%def name="title()">Configure Add-ons</%def>
<%def name="content()">
<h2 class="page-header">Configure Add-ons</h2>

<div class="row">

    <div class="col-md-3">

        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="#">Configure Add-ons</a></li>
            </ul>
        </div><!-- end sidebar -->

    </div>

    <div class="col-md-6">

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
    var checkedOnLoad = $("#selectAddonsForm input:checked");

    $('#selectAddonsForm').on('submit', function() {

        var formData = {};
        $('#selectAddonsForm').find('input').each(function(idx, elm) {
            var $elm = $(elm);
            formData[$elm.attr('name')] = $elm.is(':checked');
        });

        var unchecked = checkedOnLoad.filter($("#selectAddonsForm input:not(:checked)"));

        if(unchecked.length > 0) {
            bootbox.confirm(
                "Are you sure you want to remove the add-ons you have deselected?",
                function(result) {
                    if(result) {
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
                    }
                }
            )
        }



        return false;

    });

</script>


</%def>
