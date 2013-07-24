## http://www.webappers.com/2011/10/14/how-to-create-collapsible-tree-menu-with-pure-css/

<%def name="file_tree(files)">
    	<li class="closed"><span class="folder">${files[0].title}</span>
    	<ul>
    	% for tmp in files[1]:
    		%if isinstance(tmp, tuple):
	    		${file_tree(tmp)}
	    	%else:
	    		<li><span class="file"><a href="${files[0].url()}/files/${tmp.path}">${tmp.path}</a></span></li>
	    	%endif
	    % endfor
	    </ul>
</%def>