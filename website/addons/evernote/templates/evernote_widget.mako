<%inherit file="project/addon/widget.mako"/>
<div id="evernoteWidget">
  <div>Notebook: ${folder_name}</div>
  <div class="col-md-12">
    <div class="row">
      <button class="btn btn-success" data-bind="click: openAddDialog"></button>
    </div>
    <table>
    <thead>
      <tr>
        <th>Title</th><th>guid</th>
      </tr>
    </thead>
      <tbody data-bind="foreach: notes">
        <tr>
            <td><div data-bind="text: title"/></td>
            <td><div data-bind="text: guid"/></td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
