<!-- Authorization -->
<div>
    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        ${addon_full_name}
		<small  class=" pull-right">
				Set DOI:
				<input id="dryaddoitext" type="text" name="doi" value="${dryad_package_doi}">
				<a id="dryadsubmitkey">Submit</a><br/>
			OR: <a href="${browse_dryad_url}">Browse/Search Dryad for your package</a>
		</small>

    </h4>
</div>

<input type="hidden" id="dryad_add_url" name="browse_add_url" value="${add_dryad_package_url}" />
<input type="hidden" id="dryad_check_url" name="check_dryad_url" value="${check_dryad_url}" />

<%def name="submit_btn()"></%def>
<%def name="on_submit()"></%def>

<%include file="profile/addon_permissions.mako" />

