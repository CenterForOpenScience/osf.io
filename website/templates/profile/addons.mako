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
                <form id="selectAddonsForm" style="display: none" data-bind="submit: submitAddons">
                    <div data-bind="foreach: {data: addonCategoryData, as: 'category'}">
                        <h3 data-bind="text: category.Name"></h3>
                            <div data-bind="foreach: {data: category.Addons, as: 'addons'}">
                                <div>
                                    <input type="checkbox" data-bind="
                                    attr: {value: addons.ShortName}, 
                                    checked: $root.addonsEnabled"/>
                                    <label data-bind="text: addons.FullName"></label>
                                </div>
                            </div>
                    </div>
                    <br/>
                        <button type="submit" class="btn btn-success">
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

</%def>
<%def name="javascript_bottom()">
<script>
$script(["/static/js/addonSelector.js"]);
$script.ready("addonSelector", function(){
    new AddonSelector("#selectAddonsForm");
})
</script>
</%def>