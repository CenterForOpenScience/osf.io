<!-- TODO: File is unused; candidate for deletion? -->
<div>
    <h2>Keys</h2>
    <form id="create_key" class="form-inline">
        <div class="form-group">
            <input class="form-control" name="label" placeholder="Key label..." />
        </div>
        <button class="btn btn-default" type="submit">Create key</button>
    </form>
    % for key in keys:
        <div>
            <div class='api-credential'>
                <span class='api-key'>${key['key']}</span> |
                <span class='api-label'>${key['label']}</span>
            </div>
            <div>
                <a href="${route}key_history/${key['key']}/" class="key_history" data-key="${key['key']}">View history</a>
                <a class="revoke_key" data-key="${key['key']}">Revoke key</a>
            </div>
        </div>
    % endfor
</div>

<script type="text/javascript">
    $('#create_key').on('submit', function() {
        $.post(
            ${ '/api/v1' + route + 'create_key/' | sjson, n },
            $(this).serialize(),
            function(response) {
                window.location.reload();
            }
        );
        return false;
    });
    $('.revoke_key').on('click', function() {
        $.post(
            ${'/api/v1' + route + 'revoke_key/'},
            {key : $(this).attr('data-key')},
            function(response) {
                window.location.reload();
            }
        );
    });
</script>
