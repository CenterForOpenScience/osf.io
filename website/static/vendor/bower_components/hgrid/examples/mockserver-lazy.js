var endpoints = {
  '/grid/': [{name: 'Codes', slug: 'codes', kind: 'folder', children: []},
              {name: 'Music', slug: 'music', kind: 'folder', children: []},
              {name: "Don't open me", slug: 'error', kind: 'folder', children: []}],
  '/grid/codes': [{name: 'foo.py', kind: 'item'}, {name: 'bar.js', kind: 'item'}],
  '/grid/music': [{name: 'psycho-killer.mp3', kind: 'item'}, {name: 'Stones', kind: 'folder'}],
};

for (var url in endpoints) {
  $.mockjax({
    url: url,
    contentType: 'application/json',
    responseText: endpoints[url]
  });
}

$.mockjax({
    url: '/grid/error',
    status: 500,
    isTimeout: true,
    responseText: 'An error occurred on the server. Woops.'
});
