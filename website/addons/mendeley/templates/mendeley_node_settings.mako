<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">

    <div>
        <h4 class="addon-title">Mendeley</h4>
    </div>

    <div>
        <select class="form-control" data-bind="foreach: accounts, value: selectedAccount">
                <option data-bind="text: display_name, value: id"></option>
        </select>
        <pre data-bind="text: ko.toJSON($data, null, 2)"></pre>
        <select class="form-control" data-bind="foreach: citationLists, value: selectedCitationList">
                <option data-bind="text: name, value: provider_list_id"></option>
        </select>
    </div>


    ${self.on_submit()}

    <div class="addon-settings-message" style="display: none; padding-top: 10px;"></div>

</form>

<%def name="on_submit()">
    <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {'githubSettingsSelector': '#addonSettings${addon_short_name.capitalize()}'});
    </script>
</%def>
