<div class="well" style="padding: 8px 0;">
    <ul class="nav nav-list">
      <li class="nav-header">
          <a href="/project/${project._primary_key}/wiki/home">Project</a>
      </li>
      % if project.wiki_pages_current:
      % for k in project.wiki_pages_current.keys():
      % if not k == 'home':
       <li>
         <a href="/project/${project._primary_key}/wiki/${k}">${k}</a>
       </li>
      % endif
      % endfor
      % endif
      
      % for tnode in [x for x in project.nodes if not x.is_deleted]:
      
      <li class="nav-header">
          <a href="/project/${project._primary_key}/node/${tnode._primary_key}/wiki/home">${tnode.title} (${tnode.category})</a>
      </li>
        % if tnode.wiki_pages_current:
         % for k in tnode.wiki_pages_current.keys():
          % if not k == 'home':
           <li>
             <a href="/project/${project._primary_key}/node/${tnode._primary_key}/wiki/${k}">${k}</a>
           </li>
          %endif
          %endfor
          %endif
      %endfor
    </ul>
</div>