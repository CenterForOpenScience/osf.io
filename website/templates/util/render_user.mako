% if user_is_claimed:
<a class="overflow"
        rel="tooltip"
        href="${user_profile_url}"
        data-original-title="${user_fullname}"
    >${user_display_name}</a>
% else:
    <span class="overflow">${user_display_name}</span>
% endif
