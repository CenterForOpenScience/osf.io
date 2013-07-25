<%inherit file="project.view.mako" />
##<section id="Nodes">
##    <div class="page-header">
##        <h1>Nodes <small>The components of the project</small></h1>
##    </div>
##    <div>
##        <form class="well form-inline" action="/project/${project.id}/newnode" method="post">
##        <label>
##                <img src="/static/add_48.png" width="30px" style="vertical-align:middle;"/>
##                    Node Title
##        </label>
##        <input name="title" type="text">
##        <label>
##            Category
##        </label>
##        <select id="select01" name="category">
##        <option>Category</option>
##        %for i in ["Analysis", "Communication"]:
##        <option>${i}</option>
##        %endfor
##        </select>
##        <button type="submit" class="btn">Create Node</button>
##        </form>
##    </div>
##    <ul>
##        % if project.node:
##            % for node in project.node:
##            <li><a href="/node/${node.id}">${node.title} ${'(Public)' if project.is_public else ''}</a> | <a href="/project/${project.id}/removenode/${node.id}">remove from project</a></li>
##            % endfor
##        %endif
##    </ul>
##</section>
