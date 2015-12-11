<%inherit file="project/addon/widget.mako"/>
<div id="evernoteWidget">
  <div>Notebook: ${folder_name}</div>
  <div class="col-md-12">
    <div class="row">
      <button class="btn btn-success" data-bind="click: openAddDialog"></button>
    </div>

    <div class="row">
        <div data-bind="foreach: notes">
          <p>
            <button class="btn btn-default btn-evernote" data-bind="click: $parent.openEditDialog"
                title="Open Edit Dialog"></button>
            <button class="btn btn-danger btn-evernote" data-bind="click: $parent.openDeleteNoteDialog"
                title="Open Delete Note Dialog"></button>
          </p>
          <p>
            <span data-bind="text: title"></span>
            <span data-bind="text: guid"></span>
          </p>
        </div>
        <textarea id="evernote-notedisplay"></textarea>
      </div>

  </div>
</div>
