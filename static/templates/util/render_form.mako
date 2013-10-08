<form
    % if id:
        id="${id}"
    % endif
    name="${name}" method="${method_string}" ${"action=\""+action_string+"\"" if action_string else ""} class="${form_class}">
    <fieldset>
        % for field in form:
            <div class="form-group">
                ${field['label']}
                % if html_replacements and (field['id'] in html_replacements):
                    ${html_replacements[field['id']]}
                % else:
                    ${field['html']}
                % endif
            </div>
        % endfor
        <div class="">
          <button type="submit" class="btn btn-submit btn-primary">${submit_string}</button>
        </div>
    </fieldset>
</form>
