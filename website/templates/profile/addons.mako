<%inherit file="base.mako"/>
<%def name="title()">Configure Add-ons</%def>
<%def name="content()">
<h2 class="page-header">Configure Add-ons</h2>

<div class="row">

    <div class="col-md-3">

        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="${ web_url_for('user_profile') }">Profile Information</a></li>
                <li><a href="${ web_url_for('user_account') }">Account Settings</a></li>
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
                                            ${'checked' if (addon.short_name in addons_enabled) else ''}
                                        />
                                        ${addon.full_name}
                                    </label>
                                </div>
                            % endfor
                        % endif

                    % endfor

                    <br />

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

    // Set up submission for addon selection form
    var checkedOnLoad = $("#selectAddonsForm input:checked");

    $('#selectAddonsForm').on('submit', function() {

        var formData = {};
        $('#selectAddonsForm').find('input').each(function(idx, elm) {
            var $elm = $(elm);
            formData[$elm.attr('name')] = $elm.is(':checked');
        });

        var unchecked = checkedOnLoad.filter($("#selectAddonsForm input:not(:checked)"));

        var submit = function() {
            var request = $.osf.postJSON('/api/v1/settings/addons/', formData);
            request.done(function() {
                window.location.reload();
            });
            request.fail(function() {
                var msg = 'Sorry, we had trouble saving your settings. If this persists please contact <a href="mailto: support@osf.io">support@osf.io</a>';
                $.osf.growl('Request failed', msg);
            });
        }

        if(unchecked.length > 0) {
            var uncheckedText = $.map(unchecked, function(el){
                return ['<li>', $(el).closest('label').text().trim(), '</li>'].join('');
            }).join('');
            uncheckedText = ['<ul>', uncheckedText, '</ul>'].join('');
            bootbox.confirm({
                title: 'Are you sure you want to remove the add-ons you have deselected? ',
                message: uncheckedText,
                callback: function(result) {
                    if (result) {
                        submit();
                    } else{
                        unchecked.each(function(i, el){ $(el).prop('checked', true); });
                    }
                }
            });
        }
    else {
        submit();
    }
    return false;
    });
</script>
</%def>
