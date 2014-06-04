# hgrid-draggable.js (experimental)

Drag-and-drop support for hgrid.js.

## Dependencies

- jQuery
- HGrid >= 0.1.1

## Usage 

```html
<script src="hgrid.js"></script>
<script type="hgrid-draggable.js"></script>
```

```js
var draggable = new HGrid.Draggable({
    onDragStart: function(event, source, target) {
        #...
    },
});

var grid = new HGrid({
    # ...
})
grid.registerPlugin(draggable);

```


## Available Options

- `rowMoveManagerOptions`: Additional options passed to the `Slick.RowMoveManager` constructor
- `onMoved(event, items, folder)`


## TODO and notes

Event callbacks that receive `(event, source, destination)`

- onDrop
- onDragStart
- onDragEnd
- onDragEnter
- onDrag
- onDragLeave


## Development

Requirements

- NodeJS
- Bower

```sh
$ npm install  # installs gulp + gulp plugins
$ bower install  # installs dependencies (e.g. HGrid, qUnit...)
```


### Running tests

Tests are run using the `gulp` build tool.

```sh
$ gulp
```

You can also start watch mode

```sh
$ gulp watch
```


