<%page args="current_page=''" />

<div class="osf-affix profile-affix panel panel-default" id="usersettingspanel">
    <ul class="nav nav-stacked nav-pills">
        <li class="${'active' if current_page == 'profile' else ''}">
            <a href="${ '#' if current_page == 'profile' else web_url_for('user_profile') }">Profile information</a></li>
        <li class="${'active' if current_page == 'account' else ''}">
            <a href="${ '#' if current_page == 'account' else web_url_for('user_account') }">Account settings</a></li>
        <li class="${'active' if current_page == 'addons' else ''}">
            <a href="${ '#' if current_page == 'addons' else  web_url_for('user_addons') }">Configure add-on accounts</a></li>
        <li class="${'active' if current_page == 'notifications' else ''}">
            <a href="${ '#' if current_page == 'notifications' else web_url_for('user_notifications') }">Notifications</a></li>
        <li class="${'active' if current_page == 'dev_apps' else ''}">
            <a href="${ '#' if current_page == 'dev_apps' else web_url_for('oauth_application_list')}">Developer apps</a></li>
        <li class="${'active' if current_page == 'personal_tokens' else ''}">
            <a href="${ '#' if current_page == 'personal_tokens' else web_url_for('personal_access_token_list')}">Personal access tokens</a></li>
    </ul>
</div>


