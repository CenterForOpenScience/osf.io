<%inherit file="contentContainer.mako" />

<%
    from Framework import getUser
%>

<style type='text/css'>
    ul.project-list td ul {
        margin:0
    }
    ul.project-list td li {
        list-style-type:none
    }
    ul.project-list table.table {
        margin-bottom:0;
    }
</style>

<div class='span6'>
<h2>Newest Public Projects</h2>
    <hr>
<ul class='project-list' style='margin-left:0;'>
    ${node_list(recent_public)}
</ul>
</div>

<%def name="node_list(nodes, default=0)">
%for node in recent_public:
    <li id="projects-widget" class="project" style="display: list-item;">
        <h3 style="line-height:18px;">
                <a href="${node.url()}" style="display:inline-block; width:400px">
                    ${node.title}
                </a>
            <i style="float:right;" id="icon-${node.id}" class="icon-plus" onclick="openCloseNode('${node.id}');"></i>
        </h3>

        <div class="body hide" id="body-${node.id}" style="overflow:hidden;">
              <table class='table'>
                  <tr>
                      <th>Creator</th>
                      <td>${print_user(node.creator.id)}</td>
                  </tr>
                  <tr>
                      <th>Contributors</th>
                      <td>
                          <ul>
                          %for user_id in node.contributors:


                            <li>${print_user(user_id)}</li>
                          %endfor
                          </ul>
                      </td>
                  </tr>
              </table>


        </div>
    </li>
%endfor
</%def>

<%def name="print_user(user_id)">
<% user = getUser(user_id) %>
<a href="/profile/${user_id}">${user.fullname}</a>
</%def>