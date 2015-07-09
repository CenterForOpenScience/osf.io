<%page args="current_page=''" />

<div class="panel panel-default">
    <ul class="nav nav-stacked nav-pills">
        <li><a href="${ '#' if current_page == 'profile' else web_url_for('user_profile') }">Profile Information</a></li>
        <li><a href="${ '#' if current_page == 'account' else web_url_for('user_account') }">Account Settings</a></li>
        <li><a href="${ '#' if current_page == 'addons' else  web_url_for('user_addons') }">Configure Add-ons</a></li>
        <li><a href="${ '#' if current_page == 'notifications' else web_url_for('user_notifications') }">Notifications</a></li>
    </ul>
</div><!-- end sidebar -->
