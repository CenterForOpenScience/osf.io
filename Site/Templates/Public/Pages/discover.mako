<%inherit file="contentContainer.mako" />

<%
    from Framework import getUser
%>

<style type='text/css'>
    ul.project-list {
        margin-left:0
    }
    ul.project-list td ul {
        margin:0
    }
    ul.project-list td li {
        list-style-type:none
    }
    ul.project-list table.table {
        margin-bottom:0;
    }
    ul.project-list table.table th {
        width:100px;
    }
</style>

<div class='row'>
    <div class='span6'>
    <h2>Newest Public Projects</h2>
        <hr>
    <ul class='project-list'>
        ${node_list(recent_public_projects, prefix='newest_public')}
    </ul>
    <h2>Newest Public Registrations</h2>
        <hr>
    <ul class='project-list'>
        ${node_list(recent_public_registrations, prefix='newest_public')}
    </ul>
    </div>

    <div class='span6'>
        <h2>Most Viewed Projects</h2>
        <hr>
        <ul class='project-list'>
            ${node_list(most_viewed_projects, prefix='most_viewed')}
        </ul>
        <h2>Most Viewed Registrations</h2>
        <hr>
        <ul class='project-list'>
            ${node_list(most_viewed_registrations, prefix='most_viewed')}
        </ul>
    </div>
</div>

<%def name="node_list(nodes, default=0, prefix='')">
%for node in nodes:
    <%
        import locale
        locale.setlocale(locale.LC_ALL, 'en_US')
        unique_hits, hits = node.get_stats()
    %>
    <li class="project" style="display: list-item;">
        <h3 style="line-height:18px;">
                <a href="${node.url()}" style="display:inline-block; width:400px">
                    ${node.title}
                </a>
            <i style="float:right;" id="icon-${prefix}${node.id}" class="icon-plus" onclick="openCloseNode('${prefix}${node.id}');"></i>
        </h3>

        <div class="body hide" id="body-${prefix}${node.id}" style="overflow:hidden;">
              <table class='table'>
                  <tr>
                      <th>Description</th>
                      <td>${node.description or '<em>(No Description Set)</em>'}</td>
                  </tr>
                  <tr>
                      <th>Views</th>
                      <td>${ locale.format('%d', hits, grouping=True) if hits else 0} (${ locale.format('%d', unique_hits, grouping=True) if unique_hits else 0} unique)</td>
                  </tr>
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