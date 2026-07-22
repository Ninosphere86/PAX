import { closeSync, existsSync, mkdirSync, openSync, readFileSync, statSync, writeSync } from "node:fs";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const questions = JSON.parse(readFileSync(join(root, "app/question-bank.json"), "utf8"));
const output = join(root, "public/exports/QuestionBankImages.zip");
const publicRoot = join(root, "public");

const crcTable = new Uint32Array(256);
for (let index = 0; index < 256; index += 1) {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
  crcTable[index] = value >>> 0;
}

function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) value = crcTable[(value ^ byte) & 0xff] ^ (value >>> 8);
  return (value ^ 0xffffffff) >>> 0;
}

function imageName(question) {
  const sourceExtension = extname(question.image.split(/[?#]/)[0]).slice(1).toLowerCase() || "png";
  const extension = sourceExtension === "jpg" ? "jpeg" : sourceExtension;
  return `${question.code}.${extension}`;
}

function localHeader(name, size, checksum) {
  const filename = Buffer.from(name, "utf8");
  const header = Buffer.alloc(30 + filename.length);
  header.writeUInt32LE(0x04034b50, 0);
  header.writeUInt16LE(20, 4);
  header.writeUInt16LE(0x0800, 6);
  header.writeUInt16LE(0, 8);
  header.writeUInt16LE(0, 10);
  header.writeUInt16LE(0, 12);
  header.writeUInt32LE(checksum, 14);
  header.writeUInt32LE(size, 18);
  header.writeUInt32LE(size, 22);
  header.writeUInt16LE(filename.length, 26);
  header.writeUInt16LE(0, 28);
  filename.copy(header, 30);
  return header;
}

function centralHeader(name, size, checksum, offset) {
  const filename = Buffer.from(name, "utf8");
  const header = Buffer.alloc(46 + filename.length);
  header.writeUInt32LE(0x02014b50, 0);
  header.writeUInt16LE(20, 4);
  header.writeUInt16LE(20, 6);
  header.writeUInt16LE(0x0800, 8);
  header.writeUInt16LE(0, 10);
  header.writeUInt16LE(0, 12);
  header.writeUInt16LE(0, 14);
  header.writeUInt32LE(checksum, 16);
  header.writeUInt32LE(size, 20);
  header.writeUInt32LE(size, 24);
  header.writeUInt16LE(filename.length, 28);
  header.writeUInt16LE(0, 30);
  header.writeUInt16LE(0, 32);
  header.writeUInt16LE(0, 34);
  header.writeUInt16LE(0, 36);
  header.writeUInt32LE(0, 38);
  header.writeUInt32LE(offset, 42);
  filename.copy(header, 46);
  return header;
}

mkdirSync(dirname(output), { recursive: true });
const file = openSync(output, "w");
const central = [];
const names = new Set();
let offset = 0;
let count = 0;

try {
  for (const question of questions) {
    if (!question.image) continue;
    if (!question.image.startsWith("/") || question.image.startsWith("//")) {
      throw new Error(`${question.code}: image is not a local public asset`);
    }
    const source = resolve(publicRoot, question.image.slice(1));
    if (!source.startsWith(resolve(publicRoot) + "/") || !existsSync(source) || !statSync(source).isFile()) {
      throw new Error(`${question.code}: missing image ${question.image}`);
    }
    const name = imageName(question);
    if (names.has(name)) throw new Error(`Duplicate exported image name: ${name}`);
    names.add(name);

    const data = readFileSync(source);
    const checksum = crc32(data);
    const header = localHeader(name, data.length, checksum);
    writeSync(file, header);
    writeSync(file, data);
    central.push(centralHeader(name, data.length, checksum, offset));
    offset += header.length + data.length;
    count += 1;
  }

  const centralOffset = offset;
  for (const header of central) {
    writeSync(file, header);
    offset += header.length;
  }
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(count, 8);
  end.writeUInt16LE(count, 10);
  end.writeUInt32LE(offset - centralOffset, 12);
  end.writeUInt32LE(centralOffset, 16);
  end.writeUInt16LE(0, 20);
  writeSync(file, end);
} finally {
  closeSync(file);
}

const megabytes = (statSync(output).size / 1024 / 1024).toFixed(1);
console.log(`Wrote public/exports/QuestionBankImages.zip (${count} images, ${megabytes} MB)`);
