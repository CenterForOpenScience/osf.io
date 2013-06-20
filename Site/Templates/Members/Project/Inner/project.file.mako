<%inherit file="project.view.mako" />
<% 
	from Framework.Analytics import getBasicCounters
	from Site.Project.Model import NodeFile
	import os
%>
<div class="row">
    <div class="span8">
      	<section>
          	<div class="page-header">
            	##<div style="float:right;"><a class="btn" data-toggle="modal" href="#newNode" >New Node</a></div>
              	<h1>${file_name} (current)</h1>
          	</div>
      	</section>
      	<div>
      		${rendered}
      	</div>
    </div>
    <div class="span4">
      	<ul class="breadcrumb">
      		%if project:
  			<li><a href="${project.url()}/files">${project.title}</a> <span class="divider">/</span></li>
  			%endif
  			%if node:
  			<li><a href="${node.url()}/files">${node.title}</a> <span class="divider">/</span></li>
  			%endif
  			<li class="active">${file_name}</li>	
		</ul>
		<table class="table table-striped">
			<thead>
				<tr>
					<th>version</th>
					<th>date</th>
					<th colspan=2>downloads</th>
				</tr>
			</thead>
			<tbody>
			%for i, version in enumerate(list(reversed(node_to_use.files_versions[file_name.replace('.', '_')]))):
			<% 
				version = NodeFile.load(version) 
				base, ext = os.path.splitext(file_name)
				version_number = len(node_to_use.files_versions[file_name.replace('.', '_')])-i
				unique, total = getBasicCounters('download:' + node_to_use.id + ':' + file_name.replace('.', '_') + ':' + str(version_number))
			%>
			<tr>
				<td>
					${len(node_to_use.files_versions[file_name.replace('.', '_')])-i if i > 0 else 'current'}
				</td>
				<td>
					${version.date_uploaded.strftime('%Y/%m/%d %I:%M %p')}
				</td>
				<td>
					${str(total) if total else str(0)}
				</td>
				<td>
					<a href="${node_to_use.url()}/files/download/${file_name}/version/${version_number}"><i class="icon-download-alt"></i></a>
				</td>
			</tr>
			%endfor
			</tbody>
		</table>
    </div>
</div>