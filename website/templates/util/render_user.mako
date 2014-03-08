% if user_is_claimed:
<a
        rel="tooltip"
        href="${user_profile_url}"
        data-original-title="${user_fullname}"
    >${user_display_name}</a>
% else:
    <span>${user_display_name}</span>
% endif