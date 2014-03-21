// png-baker.js
// 2013-10-11
// Public Domain.
// For more information, see http://github.com/toolness/png-baker.js.

function PNGBaker(thing) {
  if (!(this instanceof PNGBaker)) return new PNGBaker(thing);

  var buffer = thing;

  if (typeof(thing) == 'string') buffer = this._dataURLtoBuffer(thing);

  if (!(buffer instanceof ArrayBuffer))
    throw new Error("first argument must be a data URI or ArrayBuffer");

  this.buffer = buffer;
  this.textChunks = {};
  this._chunks = [];
  this._ensurePNGsignature();
  for (var i = this.PNG_SIGNATURE.length;
       i < buffer.byteLength;
       i += this._readNextChunk(i));
  if (!this._chunks.length || this._chunks[0].type != "IHDR")
    throw new Error("first chunk must be IHDR");
  if (this._chunks[this._chunks.length-1].type != "IEND")
    throw new Error("last chunk must be IEND");
}

PNGBaker.prototype = {
  PNG_SIGNATURE: [137, 80, 78, 71, 13, 10, 26, 10],
  _ensurePNGsignature: function() {
    var bytes = new Uint8Array(this.buffer, 0, this.PNG_SIGNATURE.length);
    for (var i = 0; i < this.PNG_SIGNATURE.length; i++)
      if (bytes[i] != this.PNG_SIGNATURE[i])
        throw new Error("PNG signature mismatch at byte " + i);
  },
  _readNextChunk: function(byteOffset) {
    var i = byteOffset;
    var buffer = this.buffer;
    var data = new DataView(buffer);
    var chunkLength = data.getUint32(i); i += 4;
    var crcData = new Uint8Array(buffer, i, chunkLength+4);
    var ourCRC = this._crc32(crcData);
    var chunkType = this._arrayToStr(new Uint8Array(buffer, i, 4)); i += 4;
    var chunkBytes = new Uint8Array(buffer, i, chunkLength);

    i += chunkLength;

    var chunkCRC = data.getUint32(i); i += 4;

    if (chunkCRC != ourCRC)
      throw new Error("CRC mismatch for chunk type " + chunkType);

    if (chunkType == 'tEXt')
      this._readTextChunk(chunkBytes);
    else this._chunks.push({
      type: chunkType,
      data: chunkBytes
    });

    return i - byteOffset;
  },
  _readTextChunk: function(bytes) {
    var keyword, text;
    for (var i = 0; i < bytes.length; i++)
      if (bytes[i] == 0) {
        keyword = this._arrayToStr([].slice.call(bytes, 0, i));
        text = this._arrayToStr([].slice.call(bytes, i+1));
        break;
      }
    if (!keyword) throw new Error("malformed tEXt chunk");
    this.textChunks[keyword] = text;
  },
  _arrayToStr: function(array) {
    return [].map.call(array, function(charCode) {
      return String.fromCharCode(charCode);
    }).join('');
  },
  // http://stackoverflow.com/a/7261048
  _strToArray: function(byteString) {
    var buffer = new ArrayBuffer(byteString.length);
    var bytes = new Uint8Array(buffer);

    for (var i = 0; i < byteString.length; i++)
      bytes[i] = byteString.charCodeAt(i);
    return bytes;
  },
  // http://stackoverflow.com/a/7261048
  _dataURLtoBuffer: function(url) {
    // convert base64 to raw binary data held in a string
    // doesn't handle URLEncoded DataURIs - see SO answer #6850276 for code
    // that does this
    var byteString = atob(url.split(',')[1]);

    return this._strToArray(byteString).buffer;
  },
  // https://gist.github.com/Yaffle/1287361
  _crc32: function(s) {
    var polynomial = 0x04C11DB7,
        initialValue = 0xFFFFFFFF,
        finalXORValue = 0xFFFFFFFF,
        crc = initialValue,
        table = [], i, j, c;

    function reverse(x, n) {
      var b = 0;
      while (n) {
        b = b * 2 + x % 2;
        x /= 2;
        x -= x % 1;
        n--;
      }
      return b;
    }

    for (i = 255; i >= 0; i--) {
      c = reverse(i, 32);

      for (j = 0; j < 8; j++) {
        c = ((c * 2) ^ (((c >>> 31) % 2) * polynomial)) >>> 0;
      }

      table[i] = reverse(c, 32);
    }

    // This is a fix for Safari, which dislikes Uint8 arrays, but only
    // when Web Inspector is disabled.
    s = [].slice.call(s);

    for (i = 0; i < s.length; i++) {
      c = s[i];
      if (c > 255) {
        throw new RangeError();
      }
      j = (crc % 256) ^ c;
      crc = ((crc / 256) ^ table[j]) >>> 0;
    }

    return (crc ^ finalXORValue) >>> 0;
  },
  _makeChunk: function(chunk) {
    var i;
    var buffer = new ArrayBuffer(chunk.data.length + 12);
    var data = new DataView(buffer);
    var crcData = new Uint8Array(buffer, 4, chunk.data.length + 4);

    data.setUint32(0, chunk.data.length);
    for (i = 0; i < 4; i++)
      data.setUint8(4 + i, chunk.type.charCodeAt(i));
    for (i = 0; i < chunk.data.length; i++)
      data.setUint8(8 + i, chunk.data[i]);
    data.setUint32(8 + chunk.data.length, this._crc32(crcData));
    return buffer;
  },
  toBlob: function() {
    var parts = [new Uint8Array(this.PNG_SIGNATURE).buffer];
    var makeChunk = this._makeChunk.bind(this);

    parts.push(makeChunk(this._chunks[0]));
    parts.push.apply(parts, Object.keys(this.textChunks).map(function(k) {
      return makeChunk({
        type: 'tEXt',
        data: this._strToArray(k + '\0' + this.textChunks[k])
      });
    }, this));
    parts.push.apply(parts, this._chunks.slice(1).map(makeChunk));

    return new Blob(parts, {type: 'image/png'});
  }
};
