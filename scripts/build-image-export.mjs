import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const questions = JSON.parse(readFileSync(join(root, "app/question-bank.json"), "utf8"));
const exportDirectory = join(root, "public/exports");
const manifestPath = join(exportDirectory, "QuestionBankImages.manifest.json");
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

mkdirSync(exportDirectory, { recursive: true });
for (const existing of readdirSync(exportDirectory)) {
  if (existing.startsWith("QuestionBankImages")) unlinkSync(join(exportDirectory, existing));
}

const names = new Set();
const entries = [];
let totalImageBytes = 0;

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
  entries.push({ name, source: question.image, size: data.length, crc32: crc32(data) });
  totalImageBytes += data.length;
}

writeFileSync(
  manifestPath,
  JSON.stringify({
    filename: "QuestionBankImages.zip",
    imageCount: entries.length,
    totalImageBytes,
    entries,
  }, null, 2) + "\n",
);

console.log(`Wrote streamed ZIP manifest (${entries.length} images, ${(totalImageBytes / 1024 / 1024).toFixed(1)} MB output)`);
