<a
        % if user_is_claimed:
        rel="tooltip"
        href="${user_profile_url}"
        data-original-title="${user_fullname}"
        % endif
    >${user_display_name}</a>