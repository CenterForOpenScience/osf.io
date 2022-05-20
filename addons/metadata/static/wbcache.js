'use strict';

const $osf = require('js/osfHelpers');
const crypto = require('crypto');
const Raven = require('raven-js');

const logPrefix = '[metadata] ';

const CACHE_EXPIRATION_MSEC = 1000 * 60 * 10;

/**
 * File check processes for WaterButler.
 */
function WaterButlerCache() {
  const self = this;

  self.cache = [];

  self.setCache = function(kind, path, item, lifetime) {
    const currentTime = Date.now();
    self.cache = self.cache.filter(function(c) {
      return (c.expired <= 0 || c.expired > currentTime) && (!(c.kind === kind && c.path === path));
    });
    self.cache.push({
      created: currentTime,
      expired: lifetime === 0 ? 0 : currentTime + CACHE_EXPIRATION_MSEC,
      kind: kind,
      path: path,
      item: item,
    });
  };

  self.getCache = function(kind, path) {
    const currentTime = Date.now();
    self.cache = self.cache.filter(function(c) {
      return c.expired <= 0 || c.expired > currentTime;
    });
    const r = self.cache.filter(function(c) {
      return c.kind === kind && c.path === path;
    });
    if (r.length === 0) {
      return null;
    }
    return r[0].item;
  };

  self.clearCache = function() {
    console.log(logPrefix, 'clear cache')
    self.cache = self.cache.filter(function(c) {
      return c.expired === 0;
    });
  };

  /**
   * List all folders/files
   */
  self.listFiles = function(folder, flatten) {
    if (!folder) {
      return new Promise(function(resolve, reject) {
        const providers = self.cache.filter(function(f) {
          return f.kind === 'self' && f.path.match(/^[^\/]+\/$/);
        });
        const tasks = providers.map(function(provider) {
          return self.listFiles(provider.path, flatten);
        });
        Promise.all(tasks)
          .then(function(files) {
            if (flatten) {
              resolve(files.reduce(function(x, y) {
                return x.concat(y);
              }, []))
              return;
            }
            resolve(files);
          })
          .catch(reject);
      });
    }
    return new Promise(function(resolve, reject) {
      self.searchFiles(folder, function(items) {
        if (!items) {
          resolve([]);
          return;
        }
        const tasks = items.map(function(item) {
          return new Promise(function(resolve_, reject_) {
            if (item.attributes.kind === 'file') {
              const fileObj = {
                path: folder + item.attributes.name,
                item: item
              };
              if (flatten) {
                resolve_([fileObj]);
                return;
              }
              resolve_(fileObj);
              return;
            }
            if (item.attributes.kind !== 'folder') {
              reject_(Error('Unexpected object: ' + item.attributes.kind));
              return;
            }
            const folderPath = folder + item.attributes.name + '/';
            self.listFiles(folderPath, flatten)
              .then(function(files) {
                if (flatten) {
                  resolve_([{
                    path: folderPath,
                    item: item
                  }].concat(files));
                  return;
                }
                resolve_({
                  path: folderPath,
                  item: item,
                  children: files
                });
              })
              .catch(reject_);
          });
        });
        Promise.all(tasks)
          .then(function(files) {
            if (flatten) {
              resolve(files.reduce(function(x, y) {
                return x.concat(y);
              }, []))
              return;
            }
            resolve(files);
          })
          .catch(reject);
      });
    });
  };

  /**
   * Set the provider
   */
  self.setProvider = function(item) {
    self.setCache('self', item.data.provider + '/', item, 0);
  };

  /**
   * Search a file by path
   */
  self.searchFile = function(filepath, callback) {
    const cached = self.getCache('self', filepath);
    if (cached !== null) {
      callback(cached);
      return;
    }
    const m = filepath.match(/^(.+)\/([^\/]+)(\/?)$/);
    if (!m) {
      throw new Error('Unexpected path: ' + filepath);
    }
    const parentPath = m[1] + '/';
    const targetName = m[2];
    const folderSeparator = m[3];
    self.searchFiles(parentPath, function(parentItems) {
      if (!parentItems) {
        callback(null);
        return;
      }
      const targetFiles = parentItems.filter(function(item) {
        if (folderSeparator === '/' && item.attributes.kind !== 'folder') {
          return false;
        }
        return item.attributes.name === targetName;
      });
      if (targetFiles.length === 0) {
        callback(null);
        return;
      }
      self.setCache('self', filepath, targetFiles[0]);
      callback(targetFiles[0]);
    });
  };

  /**
   * Search files by path
   */
  self.searchFiles = function(filepath, callback) {
    const cachedItems = self.getCache('children', filepath);
    if (cachedItems !== null) {
      callback(cachedItems);
      return;
    }
    self.searchFile(filepath, function(item) {
      if (!item) {
        callback(null);
        return;
      }
      const url = new URL(self.getFileLink(item));
      url.search = '?meta=';
      $osf.ajaxJSON('GET', url.toString(), { isCors: true })
        .done(function (response) {
          console.log(logPrefix, 'files: ', response.data);
          self.setCache('children', filepath, response.data);
          callback(response.data);
        })
        .fail(function(xhr, status, error) {
          Raven.captureMessage('Error while retrieving addon info', {
            extra: {
              url: url,
              status: status,
              error: error
            }
          });
          callback(null);
        });
    });
  };

  /**
   * Get file link from item
   */
  self.getFileLink = function(item) {
    var data = item;
    if (item.data) {
      data = item.data;
    }
    if (data.links && data.links.new_folder) {
      return data.links.new_folder;
    }
    if (data.isAddonRoot) {
      var baseUrl = contextVars.waterbutlerURL;
      const m = baseUrl.match(/^(.+)\/$/);
      if (m) {
        baseUrl = m[1];
      }
      return baseUrl + '/v1/resources/' + data.nodeId + '/providers/' + data.provider + '/';
    }
    throw new Error('Unexpected item: ' + JSON.stringify(item));
  }

  /**
   * Compute a hash of the item.
   */
  self.computeHash = function(item) {
    return new Promise(function(resolve, reject) {
      if (!item.data.materialized) {
        self.setCache('self', item.data.provider + '/', item, 0);
        resolve('__PROVIDER__');
        return;
      }
      self.setCache('self', item.data.provider + item.data.materialized, item);
      if (item.kind === 'file') {
        if (item.data.etag) {
          resolve(item.data.etag);
          return;
        }
        resolve(crypto.createHash('sha256').update(item.data.name).digest('hex'));
        return;
      }
      const cached = self.getCache('children', item.data.provider + item.data.materialized);
      if (cached) {
        const filenames = (cached || []).map(function(data) {
          return data.attributes.name;
        });
        filenames.sort();
        resolve(crypto.createHash('sha256').update(filenames.join('\t')).digest('hex'));
        return;
      }
      const url = new URL(item.data.links.new_folder);
      url.search = '?meta=';
      $osf.ajaxJSON('GET', url.toString(), { isCors: true })
        .done(function (response) {
          console.log(logPrefix, 'files: ', response.data);
          self.setCache('children', item.data.provider + item.data.materialized, response.data);
          const filenames = (response.data || []).map(function(data) {
            return data.attributes.name;
          });
          filenames.sort();
          resolve(crypto.createHash('sha256').update(filenames.join('\t')).digest('hex'));
        })
        .fail(function(xhr, status, error) {
          Raven.captureMessage('Error while retrieving addon info', {
              extra: {
                  url: url,
                  status: status,
                  error: error
              }
          });
          reject(error);
        });
    });
  };
}

module.exports = {
  WaterButlerCache: WaterButlerCache,
};
