const rdmGettext = require('js/rdmGettext');

function getLocalizedText(text) {
  if (!text) {
    return text;
  }
  if (!text.includes('|')) {
    return text;
  }
  const texts = text.split('|');
  if (rdmGettext.getBrowserLang() === 'ja') {
    return texts[0];
  }
  return texts[1];
}

function normalizeText(value) {
  return value.replace(/\s+/g, ' ').trim();
}

function sizeofFormat(num) {
  // ref: website/project/util.py sizeof_fmt()
  const units = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'];
  for (var i = 0; i < units.length; i ++) {
    const unit = units[i];
    if (Math.abs(num) < 1000) {
      return Math.round(num * 10) / 10 + unit + 'B';
    }
    num /= 1000.0
  }
  return Math.round(num * 10) / 10 + 'YB';
}

module.exports = {
  getLocalizedText: getLocalizedText,
  normalizeText: normalizeText,
  sizeofFormat: sizeofFormat,
};
