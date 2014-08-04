% if user_is_claimed:
<a style="margin-right: -4px"
        rel="tooltip"
        href="${user_profile_url}"
        data-original-title="${user_fullname}"
    >${user_display_name}</a>
% else:
    <span style="margin-right: -4px">${user_display_name}</span>
% endif