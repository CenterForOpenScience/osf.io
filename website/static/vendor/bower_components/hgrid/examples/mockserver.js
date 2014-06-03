var myData = {
  data: [{
    name: 'My Computer',
    kind: 'folder',
    children: [{
      name: 'My Documents',
      kind: 'folder',
      children: [{
        name: 'Scripts',
        kind: 'folder',
        children: [{
          name: 'foo.py',
          kind: 'item'
        }, {
          name: 'Empty Folder',
          kind: 'folder'
        }]
      }, ]
    }, {
      name: 'My Music',
      kind: 'folder',
      children: [{
        name: 'bar.mp3',
        kind: 'item',
        children: []
      }]
    }]
  }]
};

$.mockjax({
  url: '/get/data',
  contentType: 'application/json',
  responseText: myData
});
