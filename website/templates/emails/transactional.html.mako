<% from website.models import Node %>

<%inherit file="notify_base.html"/>

<%def name="content">
    <table id="content" width="600" border="0" cellpadding="25" cellspacing="0" align="center" style="margin: 30px auto 0 auto;background: white;box-shadow: 0 0 2px #ccc;">
        <tbody>
            <tr>
                <td style="border-collapse: collapse;">
                    <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">Recent Activity</h3>
                </td>
            </tr>
            <tr>
                <th colspan="2" style="padding: 0px 15px 0 15px">
                    <h3 style="padding: 0 15px 5px 15px; margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300; border-bottom: 1px solid #eee; text-align: left;">
                                ${node_title}
                                %if Node.load(node_id).parent_node:
                                    <small style="font-size: 14px;color: #999;"> in ${Node.load(node_id).parent_node.title} </small>
                                %endif
                            </h3>
                </th>
            </tr>
        </tbody>
        <tbody>
            <tr>
                <td style="border-collapse: collapse;">
                    ${message}
                </td>
            </tr>
        </tbody>
    </table>
</%def>


<%def name="footer()">
<p class="small text-center" style="text-align: center;font-size: 12px; line-height: 20px;">You received this email because you are subscribed to email notifications.
  <br><a href="${url}" style="padding: 0;margin: 0;border: none;list-style: none;color: #008de5;text-decoration: none;font-weight: bold;">Update Subscription Preferences</a>
</p>
</%def>
