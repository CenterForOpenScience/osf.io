<!-- Authorization -->
<div>
    <h4 class="addon-title">Mendeley</h4>
    <table class="table">
        <tbody>
        % for account in accounts:
            <tr>
                <td>${ account['display_name'] }</td>
                <td>${ account['provider_id'] }</td>
                <td><a class="btn btn-danger">Remove</a></td>
            </tr>
        % endfor
        </tbody>
    </table>
    <a id="mendeleyConnect" class="btn btn-primary">Connect an account</a>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />