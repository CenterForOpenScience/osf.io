<dl>
	<strong>Name:</strong> <span id="pageName">${pageName}</span>
    <br />
	<strong>Version:</strong> ${version} ${'(current)' if is_current else ''}
</dl>

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