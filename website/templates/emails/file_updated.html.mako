<table class="comment-row" border="0" cellpadding="8" cellspacing="0" width="100%" align="center" style="font-size: 13px;background: #fff;border: 1px solid #eee;border-radius: 5px;margin-bottom: 10px;padding: 0px !important;">
    <tr>
        <td width="40" class="icon" valign="middle" style="border-collapse: collapse;font-size: 24px;color: #999;"> <img class="avatar" src="${profile_image_url}" width="48" alt="avatar" style="border: 0;height: auto;line-height: 100%;outline: none;text-decoration: none;border-radius: 25px;"> </td>
        <td style="line-height: 17px;border-collapse: collapse;">
            <span class="timestamp" style="color: grey;">At ${localized_timestamp}: </span>
            <span class="content" style="display: block;padding: 6px 5px 0px 8px;font-size: 14px;">
                <span class="person" style="font-weight: bold;">${user.fullname} </span>
                ${message}
                % if storage_limit_context and admin_recipient:
                    % if storage_limit_context['public']:
                        This public project is ${storage_limit_context['storage_limit_status']} the 50GB OSF Storage limit and requires your attention. In order to avoid disruption of your workflow, please take action through one of the following options:<br>
                        <ul>
                            <li>Connect an <a href="https://help.osf.io/hc/en-us/sections/360003623833-Storage-add-ons">OSF Storage add-on</a> to continue managing your research efficiently from OSF. OSF add-ons are an easy way to extend your storage space while also streamlining your data management workflow.</li>
                            <li><a href="https://help.osf.io/hc/en-us/articles/360019737614-Create-Components">Organize your project with components</a> to take advantage of the flexible structure and maximize storage options.</li>
                        </ul>
                    % else:
                        This private project is ${storage_limit_context['storage_limit_status']} the 5GB OSF Storage limit and requires your attention. In order to avoid disruption of your workflow, please take action through one of the following options:<br>
                        <ul>
                            <li>Connect an <a href="https://help.osf.io/hc/en-us/sections/360003623833-Storage-add-ons">OSF Storage add-on</a> to continue managing your research efficiently from OSF. OSF add-ons are an easy way to extend your storage space while also streamlining your data management workflow.</li>
                            <li>Free up space by making one or more of your components public. <a href="https://help.osf.io/hc/en-us/articles/360019737614-Create-Components">Organize your project with components</a> to take advantage of the flexible structure and maximize storage options.</li>
                            <li><a href="https://help.osf.io/hc/en-us/articles/360018981414-Control-Your-Privacy-Settings#Make-your-project-or-components-public">Make your project public</a> to increase storage capacity to 50 GB for files stored in OSF Storage.</li>
                        </ul>
                    % endif
                    Learn more about OSF Storage capacity limits <a href="https://help.osf.io/hc/en-us/articles/360054528874-OSF-Storage-Caps">here</a>.
                % endif
            </span>
        </td>
        <td width="25" style="text-align:center;border-collapse: collapse;font-size: 24px;border-left: 1px solid #ddd;">
            <a href="${url}" style="margin: 0;border: none;list-style: none;color: #008de5;text-decoration: none;">
                &#10095;
            </a>
        </td>
    </tr>
</table>
