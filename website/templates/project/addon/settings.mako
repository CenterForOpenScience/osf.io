<div>

    <form role="form" class="addon-settings" method="POST" data-addon="${addon_short_name}">

        <!-- Title -->
        <h4>${addon_full_name}</h4>

        ${self.body()}

        <!-- Submit button -->
        % if node and not node['is_registration']:
            <button id="addon-settings-submit" class="btn btn-success">
                Submit
            </button>
        % endif

        <!-- Form feedback -->
        <span class="addon-settings-message" style="display: none; padding-left: 10px;"></span>

    </form>

</div>
