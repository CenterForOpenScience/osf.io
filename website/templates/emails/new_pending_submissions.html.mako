<table class="comment-row" border="0" cellpadding="8" cellspacing="0" width="100%" align="center" style="font-size: 13px;background: #fff;border: 1px solid #eee;border-radius: 5px;margin-bottom: 10px;padding: 0px !important;">
    <tr>
        <td width="40" class="icon" valign="middle" style="border-collapse: collapse;font-size: 24px;color: #999;"> <img class="avatar" src="${profile_image_url}" width="48" alt="avatar" style="border: 0;height: auto;line-height: 100%;outline: none;text-decoration: none;border-radius: 25px;"> </td>
        <td style="line-height: 17px;border-collapse: collapse;">
            <span class="timestamp" style="color: grey;">At ${localized_timestamp}: </span>
            <span class="content" style="display: block;padding: 6px 5px 0px 8px;font-size: 14px;">
                % if is_request_email:
                    <span class="person" style="font-weight: bold;">${requester.fullname}</span>
                % else:
                    <span class="person" style="font-weight: bold;">${', '.join(reviewable.contributors.values_list('fullname', flat=True))}</span>
                % endif
                ${message}
            </span>
        </td>
        <td width="25" style="text-align:center;border-collapse: collapse;font-size: 24px;border-left: 1px solid #ddd;">
            <a href="${reviews_submission_url}" style="margin: 0;border: none;list-style: none;color: #008de5;text-decoration: none;">
                &#10095;
            </a>
        </td>
    </tr>
</table>
