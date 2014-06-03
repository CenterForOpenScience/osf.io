(function (global, factory) {
  if (typeof define === 'function' && define.amd) {  // AMD/RequireJS
    define(['jquery', 'hgrid'], factory);
  } else if (typeof module === 'object') {  // CommonJS/Node
    module.exports = factory(jQuery, HGrid);
  } else {  // No module system
    factory(jQuery, HGrid);
  }
}(this, function($, HGrid) {

/**
 * hgrid-draggable - Drag and drop support for HGrid
 *
 * Depends on hgrid-rowmovemanager.js and hgrid-rowselectionmodel.js.
 */
this.Draggable = (function($, HGrid) {
  'use strict';

  /**
   * Default options for the Slick.RowMoveManager constructor
   * @type {Object}
   */
  var rowMoveManagerDefaults = {
    cancelEditOnDrag: true
  };

  /**
   * Default options for Draggable constructor
   * @type {Object}
   */
  var defaults = {
    /*jshint unused: false */

    onMoved: function(event, movedItems, folder) {},
    onDrag: function(event, items) {},

    // Additional options passed to the Slick.RowMoveManager constructor
    rowMoveManagerOptions: {}
  };

  /** Public interface **/

  /**
   * Constructor for the HGrid.Draggable plugin.
   *
   * NOTE: This should NOT invoke the `init` method because `init` will be invoked
   * when HGrid#registerPlugin is called.
   */
  function Draggable(options) {
    var self = this;
    self.options = $.extend({}, defaults, options);
    self.rowMoveManager = null;  // Initialized in init
    // The current drag target
    self._folderTarget = null;
  }

  // Initialization function called by HGrid#registerPlugin
  Draggable.prototype.init = function(grid) {
    var self = this;
    var data = grid.getData();
    var dataView = grid.getDataView();
    var slickgrid = grid.grid;

    // Set selection model
    slickgrid.setSelectionModel(new HGrid.RowSelectionModel());


    // Configure the RowMoveManager
    var rowMoveManagerOptions = $.extend(
      {}, rowMoveManagerDefaults, self.options.rowMoveManagerOptions
    );
    self.rowMoveManager = new HGrid.RowMoveManager(rowMoveManagerOptions);

    /** Callbacks **/

    var onBeforeMoveRows = function(event, data) {
      // Prevent moving row before or after itself
      for (var i = 0; i < data.rows.length; i++) {
        if (data.rows[i] === data.insertBefore || data.rows[i] === data.insertBefore - 1) {
          event.stopPropagation();
          return false;
        }
      }
    };

    // TODO(sloria): Test me

    /**
     * Callback executed when rows are moved and dropped into a new location
     * on the grid.
     * @param  {Event} event
     * @param  {Object} args  Object containing information about the event,
     *                        including insertBefore.
     */
    var onMoveRows = function (event, args) {
      var extractedRows = [];
      // indices of the moved rows
      var indices = args.rows;

      // The moved data items
      var movedItems = indices.map(function(rowIdx) {
        return dataView.getItemByIdx(rowIdx);
      });

      var insertBefore = args.insertBefore;
      var left = data.slice(0, insertBefore);
      var right = data.slice(insertBefore, data.length);

      indices.sort(function(a, b) { return a - b; });

      var i;
      for (i = 0; i < indices.length; i++) {
        extractedRows.push(data[indices[i]]);
      }

      indices.reverse();

      for (i = 0; i < indices.length; i++) {
        var row = indices[i];
        if (row < insertBefore) {
          left.splice(row, 1);
        } else {
          right.splice(row - insertBefore, 1);
        }
      }

      // TODO(sloria): Is there a more performant way to do this?
      var newData = left.concat(extractedRows.concat(right));

      var selectedRows = [];
      for (i = 0; i < indices.length; i++) {
        selectedRows.push(left.length + i);
      }

      slickgrid.resetActiveCell();
      dataView.setItems(newData);
      slickgrid.setSelectedRows(selectedRows);
      slickgrid.render();
      // invoke user-defined callback
      // TODO(sloria): add target folder as an argument
      self.options.onMoved.call(self, event, movedItems);
    };

    var onDragStart = function(event, dd) {
      var cell = slickgrid.getCellFromEvent(event);
      if (!cell) {
        return;
      }

      dd.row = cell.row;
      if (!data[dd.row]) {
        return;
      }

      if (Slick.GlobalEditorLock.isActive()) {
        return;
      }

      event.stopImmediatePropagation();

      var selectedRows = grid.getSelectedRows();

      if (!selectedRows.length || $.inArray(dd.row, selectedRows) === -1) {
        selectedRows = [dd.row];
        grid.setSelectedRows(selectedRows);
      }

      dd.rows = selectedRows;
      dd.count = selectedRows.length;
    };


    var onDragRows = function(event, args) {
      // set the current drag target
      var item = grid.getItemFromEvent(event);
      if (item.kind === FOLDER) {
        self._folderTarget = item;
      } else {
        self._folderTarget = grid.getByID(item.parentID);
      }
      grid.addHighlight(self._folderTarget);

      // TODO: set target folder
      // invoke user-defined callback
      self.options.onDrag.call(self, event, args.rows);
    };

    self.rowMoveManager.onBeforeMoveRows.subscribe(onBeforeMoveRows);
    self.rowMoveManager.onMoveRows.subscribe(onMoveRows);
    self.rowMoveManager.onDragRows.subscribe(onDragRows);

    // Register the slickgrid plugin
    slickgrid.registerPlugin(self.rowMoveManager);

    slickgrid.onDragInit.subscribe(function(event) {
      // prevent grid from cancelling drag'n'drop by default
      event.stopImmediatePropagation;
    });

    slickgrid.onDragStart.subscribe(onDragStart);
  };

  Draggable.prototype.destroy = function() {
    this.rowMoveManager.destroy();
    HGrid.Col.Name.behavior = null;
  };

  HGrid.Draggable = Draggable;
  return Draggable;
}).call(this, jQuery, HGrid);

/**
 * Customized row move manager, modified from slickgrid's rowmovemanger.js (MIT Licensed)
 * https://github.com/mleibman/SlickGrid/blob/master/plugins/slick.rowmovemanager.js
 */
(function ($, HGrid) {

  function RowMoveManager(options) {
    var _grid;
    var _canvas;
    var _dragging;
    var _self = this;
    var _handler = new Slick.EventHandler();
    var _defaults = {
      cancelEditOnDrag: false
    };

    function init(grid) {
      options = $.extend(true, {}, _defaults, options);
      _grid = grid;
      _canvas = _grid.getCanvasNode();
      _handler
        .subscribe(_grid.onDragInit, handleDragInit)
        .subscribe(_grid.onDragStart, handleDragStart)
        .subscribe(_grid.onDrag, handleDrag)
        .subscribe(_grid.onDragEnd, handleDragEnd);
    }

    function destroy() {
      _handler.unsubscribeAll();
    }

    function handleDragInit(e, dd) {
      // prevent the grid from cancelling drag'n'drop by default
      e.stopImmediatePropagation();
    }

    function handleDragStart(e, dd) {
      var cell = _grid.getCellFromEvent(e);

      if (options.cancelEditOnDrag && _grid.getEditorLock().isActive()) {
        _grid.getEditorLock().cancelCurrentEdit();
      }

      if (_grid.getEditorLock().isActive() || !/move|selectAndMove/.test(_grid.getColumns()[cell.cell].behavior)) {
        return false;
      }

      _dragging = true;
      e.stopImmediatePropagation();

      var selectedRows = _grid.getSelectedRows();

      if (selectedRows.length == 0 || $.inArray(cell.row, selectedRows) == -1) {
        selectedRows = [cell.row];
        _grid.setSelectedRows(selectedRows);
      }

      var rowHeight = _grid.getOptions().rowHeight;

      dd.selectedRows = selectedRows;

      dd.selectionProxy = $("<div class='slick-reorder-proxy'/>")
          .css("position", "absolute")
          .css("zIndex", "99999")
          .css("width", $(_canvas).innerWidth())
          .css("height", rowHeight * selectedRows.length)
          .appendTo(_canvas);

      dd.guide = $("<div class='slick-reorder-guide'/>")
          .css("position", "absolute")
          .css("zIndex", "99998")
          .css("width", $(_canvas).innerWidth())
          .css("top", -1000)
          .appendTo(_canvas);

      dd.insertBefore = -1;
    }

    function handleDrag(e, dd) {
      if (!_dragging) {
        return;
      }

      e.stopImmediatePropagation();

      var top = e.pageY - $(_canvas).offset().top;
      dd.selectionProxy.css("top", top - 5);

      var insertBefore = Math.max(0, Math.min(Math.round(top / _grid.getOptions().rowHeight), _grid.getDataLength()));
      if (insertBefore !== dd.insertBefore) {
        var eventData = {
          "rows": dd.selectedRows,
          "insertBefore": insertBefore
        };

        if (_self.onBeforeMoveRows.notify(eventData) === false) {
          dd.guide.css("top", -1000);
          dd.canMove = false;
        } else {
          dd.guide.css("top", insertBefore * _grid.getOptions().rowHeight);
          dd.canMove = true;
        }

        dd.insertBefore = insertBefore;
      }
      _self.onDragRows.notify({rows: dd.selectedRows, insertBefore: dd.insertV})
    }

    function handleDragEnd(e, dd) {
      if (!_dragging) {
        return;
      }
      _dragging = false;
      e.stopImmediatePropagation();

      dd.guide.remove();
      dd.selectionProxy.remove();

      if (dd.canMove) {
        var eventData = {
          "rows": dd.selectedRows,
          "insertBefore": dd.insertBefore
        };
        // TODO:  _grid.remapCellCssClasses ?
        _self.onMoveRows.notify(eventData);
      }
    }

    $.extend(this, {
      "onBeforeMoveRows": new Slick.Event(),
      "onMoveRows": new Slick.Event(),
      'onDragRows': new Slick.Event(),
      "init": init,
      "destroy": destroy
    });
  }

  HGrid.RowMoveManager = RowMoveManager;
})(jQuery, HGrid);

/**
 * Customized row selection model, modified from slickgrid's rowselectionmodel.js (MIT Licensed)
 * https://github.com/mleibman/SlickGrid/blob/master/plugins/slick.rowselectionmodel.js
 */
(function ($, HGrid) {


    function RowSelectionModel(options) {
      var _grid;
      var _ranges = [];
      var _self = this;
      var _handler = new Slick.EventHandler();
      var _inHandler;
      var _options;
      var _defaults = {
        selectActiveRow: true
      };

      function init(grid) {
        _options = $.extend(true, {}, _defaults, options);
        _grid = grid;
        _handler.subscribe(_grid.onActiveCellChanged,
          wrapHandler(handleActiveCellChange));
        _handler.subscribe(_grid.onKeyDown,
          wrapHandler(handleKeyDown));
        _handler.subscribe(_grid.onClick,
          wrapHandler(handleClick));
      }

      function destroy() {
        _handler.unsubscribeAll();
      }

      function wrapHandler(handler) {
        return function () {
          if (!_inHandler) {
            _inHandler = true;
            handler.apply(this, arguments);
            _inHandler = false;
          }
        };
      }

      function rangesToRows(ranges) {
        var rows = [];
        for (var i = 0; i < ranges.length; i++) {
          for (var j = ranges[i].fromRow; j <= ranges[i].toRow; j++) {
            rows.push(j);
          }
        }
        return rows;
      }

      function rowsToRanges(rows) {
        var ranges = [];
        var lastCell = _grid.getColumns().length - 1;
        for (var i = 0; i < rows.length; i++) {
          ranges.push(new Slick.Range(rows[i], 0, rows[i], lastCell));
        }
        return ranges;
      }

      function getRowsRange(from, to) {
        var i, rows = [];
        for (i = from; i <= to; i++) {
          rows.push(i);
        }
        for (i = to; i < from; i++) {
          rows.push(i);
        }
        return rows;
      }

      function getSelectedRows() {
        return rangesToRows(_ranges);
      }

      function filterRowsNotInParent(rows) {
        var i, newRows = [];
        var originalRowIndex = rows[rows.length - 1];
        var gridData = _grid.getData();
        var originalRow = gridData.getItem(originalRowIndex);
        if (typeof originalRow !== 'undefined') {
          var originalParent = originalRow.parentID;
          for (i = 0; i < rows.length; i++) {
            var currentItem = gridData.getItem(rows[i]);
            if(currentItem.parentID == originalParent){
              newRows.push(rows[i]);
            }
          }
        }
        return newRows;
      }

      function setSelectedRows(rows) {
        setSelectedRanges(rowsToRanges(filterRowsNotInParent(rows)));
      }

      function setSelectedRanges(ranges) {
        _ranges = ranges;
        _self.onSelectedRangesChanged.notify(_ranges);
      }

      function getSelectedRanges() {
        return _ranges;
      }

      function handleActiveCellChange(e, data) {
        if (_options.selectActiveRow && data.row != null) {
          setSelectedRanges([new Slick.Range(data.row, 0, data.row, _grid.getColumns().length - 1)]);
        }
      }

      function handleKeyDown(e) {
        var activeRow = _grid.getActiveCell();
        if (activeRow && e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey && (e.which == 38 || e.which == 40)) {
          var selectedRows = getSelectedRows();
          selectedRows.sort(function (x, y) {
            return x - y
          });

          if (!selectedRows.length) {
            selectedRows = [activeRow.row];
          }

          var top = selectedRows[0];
          var bottom = selectedRows[selectedRows.length - 1];
          var active;

          if (e.which == 40) {
            active = activeRow.row < bottom || top == bottom ? ++bottom : ++top;
          } else {
            active = activeRow.row < bottom ? --bottom : --top;
          }

          if (active >= 0 && active < _grid.getDataLength()) {
            _grid.scrollRowIntoView(active);
            _ranges = rowsToRanges(getRowsRange(top, bottom));
            setSelectedRanges(_ranges);
          }

          e.preventDefault();
          e.stopPropagation();
        }
      }

      function handleClick(e) {
        var cell = _grid.getCellFromEvent(e);
        if (!cell || !_grid.canCellBeActive(cell.row, cell.cell)) {
          return false;
        }

        if (!_grid.getOptions().multiSelect || (
          !e.ctrlKey && !e.shiftKey && !e.metaKey)) {
          return false;
      }

      var selection = rangesToRows(_ranges);
      var idx = $.inArray(cell.row, selection);

      if (idx === -1 && (e.ctrlKey || e.metaKey)) {
        selection.push(cell.row);
        _grid.setActiveCell(cell.row, cell.cell);
      } else if (idx !== -1 && (e.ctrlKey || e.metaKey)) {
        selection = $.grep(selection, function (o, i) {
          return (o !== cell.row);
        });
        _grid.setActiveCell(cell.row, cell.cell);
      } else if (selection.length && e.shiftKey) {
        var last = selection.pop();
        var from = Math.min(cell.row, last);
        var to = Math.max(cell.row, last);
        selection = [];
        for (var i = from; i <= to; i++) {
          if (i !== last) {
            selection.push(i);
          }
        }
        selection.push(last);
        _grid.setActiveCell(cell.row, cell.cell);
      }

      _ranges = rowsToRanges(filterRowsNotInParent(selection));
      setSelectedRanges(_ranges);
      e.stopImmediatePropagation();

      return true;
    }

    $.extend(this, {
      'getSelectedRows': getSelectedRows,
      'setSelectedRows': setSelectedRows,

      'getSelectedRanges': getSelectedRanges,
      'setSelectedRanges': setSelectedRanges,

      'init': init,
      'destroy': destroy,

      'onSelectedRangesChanged': new Slick.Event()
    });
  }

  HGrid.RowSelectionModel = RowSelectionModel;
})(jQuery, HGrid);

    return Draggable;
}));
