<script type="text/html" id="registrationPreview">
  <div class="container">
    <div class="row">
      <div class="span8 col-md-2 columns eight large-8">
        <ul class="nav nav-stacked list-group" data-bind="foreach: {data: schema.pages, as: 'page'}">
          <li class="re-navbar">
            <a class="registration-editor-page" id="top-nav" style="text-align: left; font-weight:bold;" data-bind="text: title, attr.href: '#' + page.id">
            </a>
            <span class="btn-group-vertical" role="group">
              <ul class="list-group" data-bind="foreach: {data: Object.keys(page.questions), as: 'qid'}">
                <span data-bind="with: page.questions[qid]">
                  <li class="registration-editor-question list-group-item">
                    <a data-bind="text: nav, attr.href: '#' + id"></a>
                  </li>
                </span>
              </ul>
            </span>
          </li>
        </ul>
      </div>
      <div class="span8 col-md-9 columns eight large-8" style="padding-left: 30px">
        <!-- EDITOR -->
        <div data-bind="foreach: {data: schema.pages, as: 'page'}">
          <h3 data-bind="attr.id: page.id, text: page.title"></h3>
          <div class="row">
            <div data-bind="foreach: {data: Object.keys(page.questions), as: 'qid'}">
              <div class="row" data-bind="with: $parent.questions[qid]">
                <h4 data-bind="attr.id: id, text: title"></h4>
                <span data-bind="text: description"></span>
              </div>
            </div>              
          </div>
        </div>
      </div>
    </div>
  </div>
</script>
<%include file="registration_editor_templates.mako" />
