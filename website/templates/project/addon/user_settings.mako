<%inherit file="settings.mako" />

<span data-owner="user"></span>

${self.body()}

${self.submit_btn()}

${self.on_submit()}

<%def name="submit_btn()">
    <button class="btn btn-success addon-settings-submit">
        Save
    </button>
</%def>

<%def name="on_submit()">
    <script type="text/javascript">
        $(document).ready(function() {
            $('#addonSettings${addon_short_name.capitalize()}').on('submit', AddonHelper.onSubmitSettings);
        });
    </script>
</%def>
