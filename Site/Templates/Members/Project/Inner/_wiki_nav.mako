<div class="subnav">
    <ul class="nav nav-pills">
        % if is_edit:
        	%if node:
		        <li><a href="/project/${project.id}/node/${node.id}/wiki/${pageName}">View</a></li>
		    %else:
		    	<li><a href="/project/${project.id}/wiki/${pageName}">View</a></li>
		    %endif
        % else:
        	%if node:
		        <li><a href="/project/${project.id}/node/${node.id}/wiki/${pageName}/edit">Edit</a></li>
		    %else:
		    	<li><a href="/project/${project.id}/wiki/${pageName}/edit">Edit</a></li>
		    %endif
        %endif
       	%if node:
		    <li><a href="/project/${project.id}/node/${node.id}/wiki/${pageName}/compare/1">History</a></li>
		%else:
		  	<li><a href="/project/${project.id}/wiki/${pageName}/compare/1">History</a></li>
		%endif
    </ul>
</div>
