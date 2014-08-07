<div class="navbar-outer" style="overflow: hidden">
    <div style="display: inline-block">
	    <h3 class="wiki-title" id="wikiName"><span id="pageName">${pageName}</span></h3>
    </div>

    <nav class="navbar navbar-default" style="display: inline-block; float: right">
        <ul class="nav navbar-nav">
            % if user['can_edit']:
                <li><a href="#" data-toggle="modal" data-target="#newWiki">New</a></li>
                    <%include file="add_wiki_page.mako/"/>
                <li><a href="#" data-toggle="modal" data-target="#deleteWiki">Delete</a></li>
                    <%include file="delete_wiki_page.mako/"/>
            % else:
                <li><a class="disabled">New</a></li>
                <li><a class="disabled">Delete</a></li>
            % endif
        </ul>
    </nav>
</div>

%if wiki_id:
<script>
    $(document).ready(function() {
        $('#pageName').editable({
            type: 'text',
            send: 'always',
            url: '${api_url+ 'wiki/' + wiki_id + '/rename/'}',
            ajaxOptions: {
               type: 'put',
               contentType: 'application/json',
               dataType: 'json'
            },
            validate: function(value) {
              if($.trim(value) == '')
                return 'The wiki page name cannot be empty.';
            },
            params: function(params) {
               params.pk = '${wiki_id}';
               return JSON.stringify(params);
            },
            success: function(response, value){
                window.location.href = '${url + 'wiki/'}'+ value;
            },
            error: function(response) {
                if (response.status === 422){
                    return 'This is an invalid wiki page name.';
                } else if (response.status === 409) {
                    return 'A wiki page with this name already exists.';
                }
            }
        });
    });
</script>
%endif
