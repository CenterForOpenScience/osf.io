<%inherit file="project.view.mako" />
<div id='file-container' class="row">
    <div class="span8">
      	<section>
          	<div class="page-header">
              	<h1>${file_name} (current)</h1>
          	</div>
      	</section>
      	<div>
      		${rendered}
      	</div>
    </div>
    <div class="span4">
      	<ul class="breadcrumb">
            <li><a href="${node_url}files/">${node_title}</a> <span class="divider">/</span></li>
  			<li class="active">${file_name}</li>
		</ul>
		<table class="table table-striped" id='file-version-history'>
			<thead>
				<tr>
					<th>version</th>
					<th>date</th>
					<th colspan=2>downloads</th>
				</tr>
			</thead>
			<tbody>
            % for version in versions:
                <tr>
                    <td>
                        ${version['display_number']}
                    </td>
                    <td>
                        ${version['date_uploaded']}
                    </td>
                    <td>
                        ${version['total']}
                    </td>
                    <td>
                        <a href="${node_api_url}files/download/${file_name}/version/${version['number']}"><i class="icon-download-alt"></i></
                    </td>
                </tr>
			%endfor
			</tbody>
		</table>
    </div>
</div>