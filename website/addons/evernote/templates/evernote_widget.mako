##<%inherit file="project/addon/widget.mako"/>
<div id="evernoteWidget">
  <div>Hello ${full_name}!  folder_id: ${folder_id}</div>
  <div>hello var: <input data-bind="value: hello_var" /></div>
  <div>hello mirror:<span data-bind="text: hello_var"></span></div>
  <div class="col-md-12">
    <div class="row">
      <button class="btn btn-success" data-bind="click: openAddDialog"></button>
    </div>
    <table>
    <thead>
      <tr>
        <th>First name</th><th>Last name</th>
      </tr>
    </thead>
      <tbody data-bind="foreach: notes">
        <tr>
            <td><input data-bind="value: firstName"/></td>
            <td><input data-bind="value: lastName"/></td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
