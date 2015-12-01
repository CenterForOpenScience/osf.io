<!-- Authorization -->
<div>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        ${addon_full_name}
		<small  class=" pull-right">
			<form action="${add_dryad_package_url}">
				Set DOI:
				<input type="text" name="doi" value="${dryad_package_doi}">
				<input type="submit" value="Submit">
			</form>
			OR: <a href="${browse_dryad_url}">Browse/Search Dryad for your package</a>
		</small>

    </h4>
</div>

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />
<!--${context.keys()}
${context.__dict__}-->



