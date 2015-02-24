<% from website.models import User %>
<% import pytz %>
<% from pytz import timezone as tz%>

<% def localize_timestamp(user_id):
    user_timezone = tz(User.load(user_id).timezone)
    return timestamp.astimezone(user_timezone).strftime('%c')
%>

<table class="comment-row" border="0" cellpadding="8" cellspacing="0" width="100%" align="center">
    <tr>
        <td width="40" class="icon" valign="middle"> <img class="avatar" src="${gravatar_url}" width="48" alt="avatar" /> </td>
        <td style="line-height: 17px;">
            <span class="person">${User.load(commenter).fullname} </span>
            <span class="text"> commented on your ${nodeType}</span>
            <span class="timestamp"> at ${localize_timestamp(recipient_id)}: </span>
            <span class="content">"${content}"</span>
        </td>
        <td class="link text-center" width="25">
            <a href="${url}">&#10095;</a>
        </td>
    </tr>
</table>