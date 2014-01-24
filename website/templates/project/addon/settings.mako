<div>

    <form id = "${addon_short_name}" role="form" class="addon-settings" method="POST" data-addon="${addon_short_name}">

        <!-- Title -->
        <h4>${addon_full_name}</h4>

        ${next.body()}

        <!-- Form feedback -->
        <div class="addon-settings-message" style="display: none; padding-top: 10px;"></div>

    </form>

</div>
