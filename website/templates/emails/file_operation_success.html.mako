<%inherit file="notify_base.mako"/>
<%def name="content()">
    <tr>
        <td style="border-collapse: collapse;">
            <table id="content" width="600" border="0" cellpadding="25" cellspacing="0" align="center" style="margin: 30px auto 0 auto;background: white;box-shadow: 0 0 2px #ccc;">
                <tbody>
                    <tr>
                        <td style="border-collapse: collapse;">
                            <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Recent Activity</h3>
                        </td>
                    </tr>
                    <tr>
                        <th colspan="2" style="padding: 0px 15px 0 15px">
                            <h3 style="padding: 0 15px 5px 15px; margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300; border-bottom: 1px solid #eee; text-align: left;">
                              ${destination_node.title}
                              %if destination_node.parent_node:
                                <small style="font-size: 14px;color: #999;"> in ${destination_node.parent_node.title} </small>
                              %endif
                            </h3>
                        </th>
                    </tr>
                </tbody>
                <tbody>
                    <tr>
                        <td style="border-collapse: collapse;">
                          The ${'folder' if source_path.endswith('/') else 'file'} "${source_path.strip('/')}" has been successfully ${'moved' if action == 'move' else 'copied'} from ${source_addon} in ${node.title} to ${destination_addon}.
                        </td>
                    </tr>
                </tbody>
            </table>
        </td>
    </tr>
</%def>