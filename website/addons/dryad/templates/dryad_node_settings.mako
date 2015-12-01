<!-- Authorization -->
<div>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        ${addon_full_name}

        <small class="authorized-by">
            <span data-bind="if: nodeHasAuth">
                Current DOI: 
            </span>

        </small>    
    </h4>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />

<!--${context.keys()}
${context.__dict__} -->


