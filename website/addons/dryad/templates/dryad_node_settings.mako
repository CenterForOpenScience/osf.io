<!-- Authorization -->
<div>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        ${addon_full_name}
        
        <small class="authorized-by">
            % if authorized:
                    ORCID:
                        <em>${authorized_dryad_user}</em>
                <a id="dryadDelKey" class="text-danger pull-right addon-auth">Disconnect Account</a>
            % else:
                <a id="dryadAddKey" class="text-primary pull-right addon-auth">
                    Connect ORCID
                </a>
            % endif
        </small>
    </h4>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />
