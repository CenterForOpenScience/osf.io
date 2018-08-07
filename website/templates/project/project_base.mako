<%inherit file="../base.mako"/>

<%def name="resource()"><%
    if context.get('file_id'):
        prefix = 'file for a '
    else:
        prefix = ''
    if node.get('is_registration', False):
        return prefix + 'registration'
    elif node.get('is_preprint', False):
        return prefix + 'preprint'
    elif parent_node['exists']:
        return prefix + 'component'
    else:
        return prefix + 'project'
    %>
</%def>

<%def name="public()"><%
    return node.get('is_public', False)
    %>
</%def>

<%def name="description_meta()">
    %if node['description']:
        ${sanitize.strip_html(node['description']) + ' '}
    %endif
    Hosted on the Open Science Framework
</%def>

<%def name="title_meta()">
    %if node['title']:
        ${node['title']}
    %endif
</%def>

<%def name="datemodified_meta()">
    %if node['date_modified']:
        ${node['date_modified'].split('T')[0]}
    %endif
</%def>

<%def name="datecreated_meta()">
    %if node['date_created']:
        ${node['date_created'].split('T')[0]}
    %endif
</%def>

<%def name="identifier_meta()">
    <%
        identifiers = {}
        if node['identifiers']:
            identifiers = {
              'doi' : node['identifiers']['doi'],
              'ark' : node['identifiers']['ark']
            }
        return identifiers
    %>
</%def>

<%def name="license_meta()">
    %if node['license']:
        ${sanitize.strip_html(node['license']['name'])}
    %endif
</%def>

<%def name="keywords_meta()">
    %if node['tags']:
        <%
            return [tag for tag in node['tags']] + [node['category']]
        %>
    %endif
</%def>

<%def name="authors_meta()">
    %if node['contributors'] and not node['anonymous']:
        <%
            return [contrib['fullname'] for contrib in node['contributors'] if isinstance(contrib, dict)]
        %>
    %endif
</%def>

<%def name="institutions_meta()">
    %if node['institutions']:
        <%
            return [ins['name'] for ins in node['institutions'] if isinstance(ins, dict)]
        %>
    %endif
</%def>

<%def name="relations_meta()">
    <%
        relations = []
        relations.extend([
            node['registered_from_url'],
            node['forked_from_display_absolute_url'],
            node['preprint_url'] or '',
            parent_node['absolute_url'] if parent_node['exists'] else ''
        ])
        return relations
    %>
</%def>

<%def name="category_meta()">
    %if node['category']:
        ${node['category']}
    %endif
</%def>

<%def name="url_meta()">
    %if node['absolute_url']:
        ${node['absolute_url']}
    %endif
</%def>

<%def name="image_meta()">
    <%
        from website import settings
        return '{}{}/img/osf-sharing.png'.format(settings.DOMAIN.rstrip('/'), settings.STATIC_URL_PATH)
    %>
</%def>


## To change the position of alert on project pages, override alert()
<%def name="alert()"> </%def>

<%def name="content()">

<%include file="project_header.mako"/>

% if status:
    <%include file="../alert.mako"/>
% endif

<%include file="modal_show_links.mako"/>

% if node['is_retracted'] == True:
    <%include file="retracted_registration.mako" args="node='${node}'"/>
% else:
    ${next.body()}
% endif

</%def>

<%def name="javascript_bottom()">
<% from website import settings %>
<script src="/static/vendor/citeproc-js/xmldom.js"></script>
<script src="/static/vendor/citeproc-js/citeproc.js"></script>
<link href="${mfr_url}/static/css/mfr.css" media="all" rel="stylesheet" />
<script src="${mfr_url}/static/js/mfr.js"></script>

<script>

    var nodeId = ${ node['id'] |sjson, n };
    var userApiUrl = ${ user_api_url | sjson, n };
    var nodeApiUrl = ${ node['api_url'] | sjson, n };
    var absoluteUrl = ${ node['display_absolute_url'] | sjson, n };
    <%
       parent_exists = parent_node['exists']
       parent_title = ''
       parent_registration_url = ''
       parent_url = ''
       root_id = node['root_id']
       if parent_exists:
           parent_title = "Private {0}".format(parent_node['category'])
           parent_registration_url = ''
       if parent_node['can_view'] or parent_node['is_contributor']:
           parent_title = parent_node['title']
           parent_registration_url = parent_node['registrations_url']
           parent_url = parent_node['absolute_url']
    %>

    // Mako variables accessible globally
    window.contextVars = $.extend(true, {}, window.contextVars, {
        currentUser: {
            ## TODO: Abstract me
            username: ${ user['username'] | sjson, n },
            urls: {
                api: userApiUrl,
                profile: ${user_url | sjson, n}
            },
            isContributor: ${ user.get('is_contributor', False) | sjson, n },
            fullname: ${ user['fullname'] | sjson, n },
            isAdmin: ${ user.get('is_admin', False) | sjson, n},
            canComment: ${ user['can_comment'] | sjson, n},
            canEdit: ${ user['can_edit'] | sjson, n},
            profileImageUrl: ${user_profile_image | sjson, n}
        },
        node: {
            ## TODO: Abstract me
            id: nodeId,
            title: ${ node['title'] | sjson, n },
            license: ${ node['license'] | sjson, n},
            urls: {
                api: nodeApiUrl,
                web: ${ node['url'] | sjson, n },
                update: ${ node['update_url'] | sjson, n },
                waterbutlerURL: ${node['waterbutler_url']| sjson, n }
            },
            isPublic: ${ node.get('is_public', False) | sjson, n },
            isRegistration: ${ node.get('is_registration', False) | sjson, n },
            isRetracted: ${ node.get('is_retracted', False) | sjson, n },
            isPreprint: ${ node.get('is_preprint', False) | sjson, n },
            preprintFileId: ${ node.get('preprint_file_id', None) | sjson, n },
            anonymous: ${ node['anonymous'] | sjson, n },
            category: ${node['category_short'] | sjson, n },
            rootId: ${ root_id | sjson, n },
            parentTitle: ${ parent_title | sjson, n },
            parentUrl: ${ parent_url | sjson, n },
            parentRegisterUrl: ${parent_registration_url | sjson, n },
            parentExists: ${ parent_exists | sjson, n},
            childExists: ${ node['child_exists'] | sjson, n},
            registrationMetaSchemas: ${ node['registered_schemas'] | sjson, n },
            registrationMetaData: ${ node['registered_meta'] | sjson, n },
            contributors: ${ node['contributors'] | sjson, n },
        }
    });
</script>
<script type="text/x-mathjax-config">
    MathJax.Hub.Config({
        tex2jax: {inlineMath: [['$','$'], ['\\(','\\)']], processEscapes: true},
        // Don't automatically typeset the whole page. Must explicitly use MathJax.Hub.Typeset
        skipStartupTypeset: true
    });
</script>

<script type="text/javascript"
% if settings.USE_CDN_FOR_CLIENT_LIBS:
    src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.2/MathJax.js?config=TeX-AMS-MML_HTMLorMML"
% else:
    src="/static/vendor/bower_components/MathJax/unpacked/MathJax.js?config=TeX-AMS-MML_HTMLorMML"
% endif
></script>

<script src=${"/static/public/js/project-base-page.js" | webpack_asset}> </script>
</%def>
