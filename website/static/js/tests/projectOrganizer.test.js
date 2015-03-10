/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var $ = require('jquery');
var moment = require('moment');
var Raven = require('raven-js');

var ProjectOrganizer = require('projectOrganizer');

// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
sinon.assert.expose(assert, {prefix: ''});

var returnTrue = function() {
    return true;
};

var returnFalse = function() {
    return false;
};

var parentIsFolder = function(){
    return {
        data: {
            node_id: 'normalFolder'
        }
    };
};

var parentIsNotFolder = function(){
    return {
        data: {
            node_id: 'noParent'
        }
    };
};

describe('ProjectOrganizer', () => {
    var parent = {
        name: 'Parent',
        isAncestor: returnTrue
    };

    var child = {
        name: 'Child',
        isAncestor: returnFalse
    };

    describe('whichIsContainer', () => {
        it('says children are contained in parents', () => {
            var ancestor = ProjectOrganizer._whichIsContainer(parent, child);
            assert.equal(ancestor.name, 'Parent');
        });

        it('says parents contain children', () => {
            var ancestor = ProjectOrganizer._whichIsContainer(child, parent);
            assert.equal(ancestor.name, 'Parent');
        });
        it('says nothing if both contain each other', () => {
            var ancestor = ProjectOrganizer._whichIsContainer(parent, parent);
            assert.equal(ancestor, null);
        });
        it('says nothing if neither contains the other', () => {
            var ancestor = ProjectOrganizer._whichIsContainer(child, child);
            assert.equal(ancestor, null);
        });
    });

    describe('canAcceptDrop', () => {
        var normalFolder = {
            data: {
                isFolder: true,
                isSmartFolder: false,
                node_id: 'normalFolder',
                permissions: {
                    acceptsComponents: true,
                    acceptsFolders: true,
                    acceptsMoves: true,
                    acceptsCopies: true
                }
            }
        };

        var canCopyOrMoveItem = {
            isAncestor: returnFalse,
            id: 'canCopyItem',
            parent: parentIsNotFolder,
            data: {
                isComponent: false,
                isFolder: false,
                permissions: {
                    copyable: true,
                    movable: true
                }
            }
        };
        var cannotCopyOrMoveItem = {
            isAncestor: returnFalse,
            id: 'canCopyItem',
            parent: parentIsNotFolder,
            data: {
                isComponent: false,
                isFolder: false,
                permissions: {
                    copyable: false,
                    movable: false
                }
            }
        };

        it('rejects non-folders', () => {
            var nonFolder = {
                data: {
                    isFolder: false,
                    isSmartFolder: false,
                    node_id: 'nonFolder',
                    permissions: {
                        acceptsComponents: false,
                        acceptsFolders: false,
                        acceptsMoves: false,
                        acceptsCopies: false
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([canCopyOrMoveItem], nonFolder);
            assert.equal(result, false);
        });

        it('rejects smart folders', () => {
            var smartFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: true,
                    node_id: 'smartFolder',
                    permissions: {
                        acceptsComponents: false,
                        acceptsFolders: false,
                        acceptsMoves: false,
                        acceptsCopies: false
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([canCopyOrMoveItem], smartFolder);
            assert.equal(result, false);
        });

        it('rejects if target is contained by dropped items', () => {
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true
                    }
                }
            };

            var canCopyOrMoveItem = {
                isAncestor: returnTrue,
                id: 'canCopyItem',
                parent: parentIsNotFolder,
                    data: {
                        isComponent: false,
                        isFolder: false,
                        permissions: {
                            copyable: true,
                            movable: true
                        }
                    }
                };

            var result = ProjectOrganizer._canAcceptDrop([canCopyOrMoveItem], normalFolder);
            assert.equal(result, false);
        });

        it('rejects dropping on its source folder', () => {
            var normalCopyableFolder = {
                isAncestor: returnFalse,
                id: 'normalFolder',
                data: {

                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    parent: parentIsNotFolder,
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true,
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([normalCopyableFolder], normalCopyableFolder);
            assert.equal(result, false);
        });

        it('rejects components if target does not accept components', () => {
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: false,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true
                    }
                }
            };

            var canCopyOrMoveItem = {
                isAncestor: returnFalse,
                id: 'canCopyItem',
                parent: parentIsNotFolder,
                data: {
                    isComponent: true,
                    isFolder: false,
                    permissions: {
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([canCopyOrMoveItem], normalFolder);
            assert.equal(result, false);
        });

        it('accepts components if target accepts components', () => {
            var copyMode = 'copy';
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true
                    }
                }
            };

            var canCopyComponent = {
                isAncestor: returnFalse,
                id: 'canCopyItem',
                parent: parentIsNotFolder,
                data: {
                    isComponent: true,
                    isFolder: false,
                    permissions: {
                        copyable: true,
                        movable: false
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([canCopyComponent], normalFolder, copyMode);
            assert.equal(result, true);
        });

        it('rejects folders if target does not accept folders', () => {
            var copyMode = 'move';
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: false,
                        acceptsMoves: true,
                        acceptsCopies: true
                    }
                }
            };

            var normalMovableFolder = {
                isAncestor: returnFalse,
                id: 'normalFolder',
                parent: parentIsNotFolder,
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true,
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([normalMovableFolder], normalFolder, copyMode);
            assert.equal(result, false);
        });

        it('rejects any folder if target does not accept folders', () => {
            var copyMode = 'move';
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: false,
                        acceptsMoves: true,
                        acceptsCopies: true
                    }
                }
            };

            var normalMovableFolder = {
                isAncestor: returnFalse,
                id: 'normalFolder',
                parent: parentIsNotFolder,
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true,
                        copyable: true,
                        movable: true
                    }
                }
            };

            var canMoveItem = {
                isAncestor: returnFalse,
                id: 'canCopyItem',
                parent: parentIsNotFolder,
                data: {
                    isComponent: false,
                    isFolder: false,
                    permissions: {
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([canMoveItem, normalMovableFolder, canMoveItem], normalFolder, copyMode);
            assert.equal(result, false);
        });


        it('accepts folders if target accepts folders', () => {
            var copyMode = 'move';
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true
                    }
                }
            };

            var normalMovableFolder = {
                isAncestor: returnFalse,
                id: 'normalFolder',
                parent: parentIsNotFolder,
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true,
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([normalMovableFolder], normalFolder, copyMode);
            assert.equal(result, true);
        });

        it('rejects if copyMode is move and target does not accept move', () => {
            var copyMode = 'move';
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: false,
                        acceptsCopies: true
                    }
                }
            };

            var normalMovableFolder = {
                isAncestor: returnFalse,
                id: 'normalFolder',
                parent: parentIsNotFolder,
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true,
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([normalMovableFolder], normalFolder, copyMode);
            assert.equal(result, false);
        });

        it('accepts if copyMode is move and target accepts move', () => {
            var copyMode = 'move';
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true
                    }
                }
            };

            var normalMovableFolder = {
                isAncestor: returnFalse,
                id: 'normalFolder',
                parent: parentIsNotFolder,
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true,
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([normalMovableFolder], normalFolder, copyMode);
            assert.equal(result, true);
        });

        it('rejects if copyMode is copy and target does not accept copy', () => {
            var copyMode = 'copy';
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: false
                    }
                }
            };

            var normalMovableFolder = {
                isAncestor: returnFalse,
                id: 'normalFolder',
                parent: parentIsNotFolder,
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true,
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([normalMovableFolder], normalFolder, copyMode);
            assert.equal(result, false);


        });

        it('accepts if copyMode is copy and target accepts copy', () => {
            var copyMode = 'copy';
            var normalFolder = {
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true
                    }
                }
            };

            var normalMovableFolder = {
                isAncestor: returnFalse,
                id: 'normalFolder',
                parent: parentIsNotFolder,
                data: {
                    isFolder: true,
                    isSmartFolder: false,
                    node_id: 'normalFolder',
                    permissions: {
                        acceptsComponents: true,
                        acceptsFolders: true,
                        acceptsMoves: true,
                        acceptsCopies: true,
                        copyable: true,
                        movable: true
                    }
                }
            };

            var result = ProjectOrganizer._canAcceptDrop([normalMovableFolder], normalFolder, copyMode);
            assert.equal(result, true);

        });


    });
});