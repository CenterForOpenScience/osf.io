% if user_is_claimed:
<a class="overflow contributor-name"
        rel="tooltip"
        href="${user_profile_url}"
        data-original-title="${user_fullname}"
    >${user_display_name}</a>
% else:
    <span class="overflow contributor-name">${user_display_name}</span>
% endif