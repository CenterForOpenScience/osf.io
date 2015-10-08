<!-- String Types -->
<script type="text/html" id="string">
  <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="text">
  <input data-bind="valueUpdate: 'keyup',
                    value: value"
         type="text" class="form-control" />
</script>
<script type="text/html" id="match">
  <input data-bind="valueUpdate: 'keyup',
                    value: value,
                    attr.placeholder: match" type="text" class="form-control" />
</script>
## TODO(hrybacki): valueUpdate doesn't work with textarea(s), as a result throttling is not
## possible and we must call `save` on via the event binding. We still have throttling in
## place for the other fields but this will need to be resolved with what will likely be a
## convoluted solution.on.
<script type="text/html" id="textarea">
  <textarea data-bind="valueUpdate: 'keyup',
                       event: {'keyup': save},
                       textInput: value"
            class="form-control"> </textarea>
</script>
<!-- Number Types -->
<script type="text/html" id="number">
  <input data-bind="valueUpdate: 'keyup',
                    value: value" type="text" class="form-control">
</script>
<!-- Enum Types -->
<script type="text/html" id="choose">
  <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="singleselect">
  <div class="col-md-12" data-bind="foreach: {data: options, as: 'option'}">
    <p>
      <input type="radio" data-bind="event: {
                                       'click': $parent.save
                                     },
                                     checked: $parent.value,
                                     value: option"/>
      <span data-bind="text: option"></span>
    </p>
  </div>
</script>

<script type="text/html" id="object">
  <span data-bind="foreach: {data: $root.iterObject($data.properties)}">
      <div data-bind="template: {data: $root.context(value), name: value.type}"></div>
      <hr />
    </span>
  </span>
</script>

<!-- Base Template -->
<script type="text/html" id="editorBase">
  <div class="well" style="padding-bottom: 0px;">
    <div class="row">
      <div class="col-md-12">
        <div class="form-group">
          <label class="control-label" data-bind="text: title"></label>
          <p class="help-block" data-bind="text: description"></p>
          <span data-bind="if: help" class="example-block">
            <a data-bind="click: toggleExample">Show Example</a>
            <p data-bind="visible: showExample, text: help"></p>
          </span>
          <br />
          <br />
          <div class="row">
            <div class="col-md-12">
              <div class="form-group" data-bind="css: {has-success: $data.value.isValid}">
                <span data-bind="with: $root.context($data)">
                  <span data-bind="if: $root.showValidation">
                    <p class="text-error" data-bind="validationMessage: $data.value"></p>
                    <ul class="list-group" data-bind="foreach: $data.validationMessages">
                      <li class="list-group-item">
                        <span class="text-danger"
                              data-bind="text: $data">
                        </span>
                      </li>
                    </ul>
                  </span>
                  <div data-bind="template: {data: $data, name: type}"></div>
                </span>
              </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</script>
<script type="text/html" id="editor">
  <span data-bind="template: {data: $data, name: 'editorBase'}"></span>
</script>

<%include file="registration_editor_extensions.mako" />
