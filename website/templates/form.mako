<%page args="
    form,
    name,
    actionString=None,
    methodString='post',
    formClass='form-stacked',
    submitString='Create Account',
    htmlReplacements=None,
    fieldNamePrefix='',
    id=None
" />
<form
    % if id:
        id="${id}"
    % endif
    name="${name}" method="${methodString}" ${"action=\""+actionString+"\"" if actionString else ""} class="${formClass}">
    <fieldset>
        % for field in form:
            <div class="form-group">
                ${field.label}
                <div class="input">
                    % if htmlReplacements and (field.id in htmlReplacements):
                        ${htmlReplacements[field.id]}
                    % else:
                        ${field}
                    % endif
                </div>
            </div>
        % endfor
          <button class="btn btn-primary btn-submit" type="submit">${submitString}</button>
    </fieldset>
</form>
