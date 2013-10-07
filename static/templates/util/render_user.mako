<a
        rel="tooltip"
        href="${user_profile_url}"
        data-original-title="${user_fullname}"
    >
    ${user_display_name}
</a>
##<%
##    user = get_user(user_id)
##    name_formatters = {
##        'long': lambda: user.fullname,
##        'surname': lambda: user.surname,
##        'initials': lambda: u'{surname}, {initial}.'.format(
##            surname=user.surname,
##            initial=user.given_name_initial
##        ),
##    }
##    user_display_name = name_formatters[format]()
##%>
##<a rel='tooltip' href='/profile/${user_profile_url}' data-original-title='${user.fullname}'>${user_display_name}</a></%def>