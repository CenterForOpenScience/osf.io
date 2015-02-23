<% from website.models import User %>
<% from datetime import datetime%>
<% from dateutil.relativedelta import relativedelta%>

<% def localize_timestamp(user_id):
    return (timestamp - relativedelta(minutes=User.load(user_id).timezone_offset)).strftime('%H:%M on %A, %B %d')
%>

<table class="comment-row" border="0" cellpadding="8" cellspacing="0" width="100%" align="center">
    <tr>
        <td width="40" class="icon" valign="middle"> <img class="avatar" src="${gravatar_url}" width="48" alt="avatar" /> </td>
        <td style="line-height: 17px;">
            <span class="person">${User.load(commenter).fullname} </span>
            <span class="text"> replied to your comment "${parent_comment}" on your ${nodeType} </span>
            <span class="timestamp"> at ${localize_timestamp(commenter)}: </span>
            <span class="content">"${content}"</span>
        </td>
        <td class="link text-center" width="25">
            <a href="${url}">&#10095;</a>
        </td>
    </tr>
</table>