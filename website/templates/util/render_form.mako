<form
    % if id:
        id="${id}"
    % endif
    name="${name}" method="${method_string}" action="${action_string}" class="${form_class}">
    <fieldset>
        % for field in form:
            <div class="form-group">
                ${field['label'] | unicode, n }
                <span class="help-block">${ field['description'] | unicode, n }</span>
                % if html_replacements and (field['id'] in html_replacements):
                    ${ html_replacements[field['id']] | unicode, n }  <!-- possibly totally unused -->
                % else:
                    ${ field['html'] | unicode, n }
                % endif
            </div>
        % endfor
        % if next_url:
            <input type="hidden" name="next_url" value="${next_url}" />
        % endif
        <div class="">
          <button type="submit" class="btn btn-submit ${submit_btn_class or 'btn-primary'}">${submit_string}</button>
        </div>
    </fieldset>
</form>
