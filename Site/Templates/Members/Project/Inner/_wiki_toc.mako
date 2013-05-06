<div class="well" style="padding: 8px 0;">
    <ul class="nav nav-list">
      <li class="nav-header">
          <a href="/project/${project.id}/wiki/home">Project</a>
      </li>
      % if project.wiki_pages_current:
      % for k in project.wiki_pages_current.keys():
      % if not k == 'home':
       <li>
         <a href="/project/${project.id}/wiki/${k}">${k}</a>
       </li>
      % endif
      % endfor
      % endif
      
      % for tnode in project.nodes.objects():
      
      <li class="nav-header">
          <a href="/project/${project.id}/node/${tnode.id}/wiki/home">${tnode.title} (${tnode.category})</a>
      </li>
        % if tnode.wiki_pages_current:
         % for k in tnode.wiki_pages_current.keys():
          % if not k == 'home':
           <li>
             <a href="/project/${project.id}/node/${tnode.id}/wiki/${k}">${k}</a>
           </li>
          %endif
          %endfor
          %endif
      %endfor
    </ul>
</div>