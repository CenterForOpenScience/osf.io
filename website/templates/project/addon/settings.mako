<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">

    <!-- Title -->
    ${self.title()}

    ${next.body()}

    <!-- Form feedback -->
    <div class="addon-settings-message" style="display: none; padding-top: 10px;"></div>

</form>

<%def name="title()">
    <h4>${addon_full_name}</h4>
</%def>
