<%inherit file="notify_base.mako" />

## submitter name come from the account being reported

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
  <h3 class="text-center" style="padding: 0;margin: 30px 0 0 0;border: none;list-style: none;font-weight: 300;text-align: center;">${moderator__id | h} has reported ${resource__id | h} as spam</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">
      Moderator: <a href="${moderator_absolute_url | h}">${moderator_fullname | h}</a> [${moderator__id | h}]
    <br />
      Reported ${document_type | h}: <a href="${resource_absolute_url | h}">${resource_title | h}</a> [${resource__id | h}]
    <br />
      Provider: ${provider_name | h}
    <br />
      Submitted by: <a href="${resource_creator_absolute_url | h}">${resource_creator_fullname | h}</a> [${resource_creator__id | h}]
    % if resource_admin_app_url:
    <br />
      Review in admin: <a href="${resource_admin_app_url | h}">${resource_admin_app_url | h}</a>
    % endif
    % if creator_admin_app_url:
    <br />
      Disable this account: <a href="${creator_admin_app_url | h}">${creator_admin_app_url | h}</a>
    % endif

    % if comment:
    <br />
      Remarks from the moderator: ${comment | h}
    % endif
  </td>
</tr>
</%def>
