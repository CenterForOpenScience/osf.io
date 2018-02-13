
%if node['is_public'] or user['has_read_permissions']:
    <%include file="project/project.mako"/>
%elif node['access_requests_enabled']:
    <%include file="project/request_access.mako"/>
%endif
