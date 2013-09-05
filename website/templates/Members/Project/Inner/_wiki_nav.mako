<%
    node_to_use = node or project
    is_contributor = node_to_use.is_contributor(user)
    editable = is_contributor and not node_to_use.is_registration
%>

<div class="subnav">
    <ul class="nav nav-pills">
        % if is_edit:
        	%if node:
		        <li><a href="/project/${project._primary_key}/node/${node._primary_key}/wiki/${pageName}">View</a></li>
		    %else:
		    	<li><a href="/project/${project._primary_key}/wiki/${pageName}">View</a></li>
		    %endif
        % else:
            % if editable:
                %if node:
                    <li><a href="/project/${project._primary_key}/node/${node._primary_key}/wiki/${pageName}/edit">Edit</a></li>
                % else:
                    <li><a href="/project/${project._primary_key}/wiki/${pageName}/edit">Edit</a></li>
                % endif
            % else:
                <li><a class="disabled">Edit</a></li>
            % endif
        %endif
       	%if node:
		    <li><a href="/project/${project._primary_key}/node/${node._primary_key}/wiki/${pageName}/compare/1">History</a></li>
		%else:
		  	<li><a href="/project/${project._primary_key}/wiki/${pageName}/compare/1">History</a></li>
		%endif
    </ul>
</div>
