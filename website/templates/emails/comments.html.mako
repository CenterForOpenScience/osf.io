<% from website.models import User %>

<table class="comment-row" border="0" cellpadding="8" cellspacing="0" width="100%" align="center">
    <tr>
        <td width="40" class="icon" valign="middle"> <img class="avatar" src="${gravatar_url}" width="48" alt="avatar" /> </td>
        <td style="line-height: 17px;">
            <span class="person">${commenter.fullname} </span>
            <span class="text"> commented on your ${nodeType}</span>
            <span class="timestamp"> at ${localized_timestamp}: </span>
            <span class="content">"${content}"</span>
        </td>
        <td class="link text-center" width="25">
            <a href="${url}">&#10095;</a>
        </td>
    </tr>
</table>