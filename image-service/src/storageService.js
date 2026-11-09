const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { Jimp } = require('jimp');
const config = require('./config');
const db = require('./database');

if (!fs.existsSync(config.STORAGE_DIR)) {
  fs.mkdirSync(config.STORAGE_DIR, { recursive: true });
}

function createSlug(prompt) {
  return prompt
    .toLowerCase()
    .replace(/[^a-z0-9 ]/gi, '')
    .trim()
    .replace(/\s+/g, ' ');
}

function calculateSha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function generateNaming(prompt, aiCode, ext) {
  aiCode = aiCode || config.AI_ID;
  ext = (ext || 'png').replace(/^\./, '').toLowerCase();
  const slug = createSlug(prompt);
  const imageName = slug + ' ' + aiCode + '.' + ext;
  const uuid4hex = crypto.randomUUID().replace(/-/g, '');
  const storageKey = slug.replace(/\s+/g, '-') + '/' + aiCode + '/' + uuid4hex + '.' + ext;
  return { slug, imageName, storageKey, extension: ext };
}

/**
 * FIX: Tra URL tuyet doi su dung config.BASE_URL
 * De B4.3 Frontend va B4.4 Gateway co the goi truc tiep
 * Vi du: http://192.168.100.12:8002/static/black%20dog%202.1.png
 */
function buildFileUrl(imageName) {
  return config.BASE_URL + '/static/' + encodeURIComponent(imageName);
}

async function storeImage({ buffer, prompt, aiCode, styleId, customFilename }) {
  aiCode = aiCode || config.AI_ID;
  styleId = styleId || 'deco-v1';

  if (!buffer || buffer.length === 0) {
    throw new Error('Du lieu buffer anh rong.');
  }

  // Chong trung lap bang SHA-256
  const sha256 = calculateSha256(buffer);
  const existingByHash = db.findImageByHash(sha256);
  if (existingByHash) {
    db.logActivity('DUPLICATE_PREVENTED', 'SHA-256 trung: ' + existingByHash.image_id);
    return {
      status: 'duplicate',
      message: 'Anh da ton tai (SHA-256: ' + sha256.substring(0, 12) + '...)',
      image: existingByHash,
    };
  }

  // Doc thong tin anh bang Jimp
  let width = 256, height = 256, format = 'PNG';
  try {
    const jimpImage = await Jimp.read(buffer);
    width = jimpImage.bitmap.width;
    height = jimpImage.bitmap.height;
    format = jimpImage.mime ? jimpImage.mime.split('/')[1].toUpperCase() : 'PNG';
  } catch (err) {
    console.warn('Jimp warning:', err.message);
  }

  const naming = generateNaming(prompt, aiCode, format.toLowerCase());
  const imageName = customFilename || naming.imageName;
  const slug = naming.slug;
  const storageKey = naming.storageKey;

  // Luu file vat ly
  fs.writeFileSync(path.join(config.STORAGE_DIR, imageName), buffer);
  const s3Path = path.join(config.STORAGE_DIR, storageKey);
  fs.mkdirSync(path.dirname(s3Path), { recursive: true });
  fs.writeFileSync(s3Path, buffer);

  // Ghi database voi file_url TUYET DOI
  const record = {
    image_id: crypto.randomUUID(),
    image_name: imageName,
    slug,
    prompt: prompt.trim().toLowerCase(),
    style_id: styleId,
    worker_id: 'W' + aiCode.split('.')[0],
    ai_code: aiCode,
    storage_key: storageKey,
    sha256,
    width, height, format,
    file_size: buffer.length,
    file_url: buildFileUrl(imageName),  // FIX: URL tuyet doi
    created_at: new Date().toISOString(),
  };

  const savedRecord = db.insertImage(record);
  db.logActivity('IMAGE_STORED', 'Luu anh: ' + imageName + ' by AI ' + aiCode);

  return {
    status: 'success',
    message: 'Anh da duoc luu thanh cong.',
    image: savedRecord,
  };
}

function removeImage(id) {
  const image = db.getImageById(id);
  if (!image) return null;
  try {
    const p1 = path.join(config.STORAGE_DIR, image.image_name);
    if (fs.existsSync(p1)) fs.unlinkSync(p1);
    const p2 = path.join(config.STORAGE_DIR, image.storage_key);
    if (fs.existsSync(p2)) fs.unlinkSync(p2);
  } catch (err) {
    console.error('Loi xoa file:', err);
  }
  db.deleteImageById(id);
  db.logActivity('IMAGE_DELETED', 'Xoa anh: ' + image.image_name);
  return image;
}

module.exports = { createSlug, calculateSha256, generateNaming, buildFileUrl, storeImage, removeImage };
