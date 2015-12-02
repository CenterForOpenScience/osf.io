<!-- Authorization -->
<%inherit file="project/addon/user_settings.mako" />
<div>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        ${FULL_NAME}
    </h4>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />
