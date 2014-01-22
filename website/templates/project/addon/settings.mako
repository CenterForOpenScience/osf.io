<div>

    <form role="form" class="addon-settings" method="POST" data-addon="${addon_short_name}">

        <!-- Title -->
        <h4>${addon_full_name}</h4>

        ${self.body()}

        % if node and not node['is_registration'] or show_submit:
            <button id="addon-settings-submit" class="btn btn-success">
                Submit
            </button>
        % endif

        <!-- Form feedback -->
        <div class="addon-settings-message" style="display: none; padding-top: 10px;"></div>

    </form>

</div>
