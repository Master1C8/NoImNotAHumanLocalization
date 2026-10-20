#!/usr/bin/env node
// Local-only encoding using the site's actual optimizeMediaPreview function.
// No production connections, uploads, site dependencies, or site files change.
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { readFile, writeFile, readdir, mkdir, access, rename } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [sourceRootArg, outputRootArg, toolsRootArg] = process.argv.slice(2);
if (!sourceRootArg || !outputRootArg || !toolsRootArg) throw new Error('Usage: prepare_site_screenshots.mjs <flat-png-root> <new-output-root> <temporary-tools-root>');
const sourceRoot = path.resolve(sourceRootArg), outputRoot = path.resolve(outputRootArg), toolsRoot = path.resolve(toolsRootArg);
const require = createRequire(path.join(toolsRoot, 'package.json'));
const sharp = require('sharp'), esbuild = require('esbuild');
const canonicalPath = '/Users/antonkrutov/Desktop/SiteForMods/lib/media-optimization.ts';
const canonicalSource = await readFile(canonicalPath, 'utf8');
const sharpPath = require.resolve('sharp');
const { code } = await esbuild.transform(canonicalSource.replace('from "sharp";', `from ${JSON.stringify(sharpPath)};`), { loader: 'ts', format: 'esm', target: 'node22' });
const compiledPath = path.join(toolsRoot, 'canonical-media-optimization.mjs');
await writeFile(compiledPath, code);
const media = await import(pathToFileURL(compiledPath).href);
const entries = await readdir(sourceRoot, { withFileTypes: true });
if (entries.length !== 6 || entries.some(e => !e.isFile() || !/^ru-0[1-6]-.+\.png$/.test(e.name))) throw new Error('Expected exactly six flat Russian PNGs');
try { await access(outputRoot); throw new Error('Output already exists'); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const stagingRoot = `${outputRoot}.partial-${process.pid}`;
await mkdir(stagingRoot);
await mkdir(path.join(stagingRoot, 'variants'));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const hashes = new Set(), frames = [];
for (const entry of entries.sort((a,b) => a.name.localeCompare(b.name))) {
  const source = await readFile(path.join(sourceRoot, entry.name));
  if (source.length > 25 * 1024 * 1024 || !source.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) throw new Error('Invalid PNG input');
  if (hashes.has(sha(source))) throw new Error('Duplicate screenshot content');
  hashes.add(sha(source));
  const sourceMetadata = await sharp(source, {failOn: 'error'}).metadata();
  const preview = await media.optimizeMediaPreview(source);
  const row = {source: entry.name, sourceSha256: sha(source), sourceBytes: source.length, sourceDimensions: [sourceMetadata.width, sourceMetadata.height], outputs: {}};
  for (const [role, bytes] of Object.entries(preview)) {
    const base = entry.name.replace(/\.png$/, '');
    const filename = role === 'original' ? `${base}.webp` : `variants/${base}-${role}.webp`;
    const metadata = await sharp(bytes, {failOn:'error'}).metadata();
    if (metadata.format !== 'webp' || metadata.width > 1920 || metadata.height > 1920 || metadata.exif || metadata.icc || metadata.xmp) throw new Error('Invalid optimized format, dimensions or metadata');
    if (role === 'cover' && (metadata.width !== 1280 || metadata.height !== 720)) throw new Error('Cover dimensions differ');
    if (role === 'thumbnail' && (metadata.width !== 360 || metadata.height !== 203)) throw new Error('Thumbnail dimensions differ');
    await writeFile(path.join(stagingRoot, filename), bytes, {flag:'wx'});
    if (sha(await readFile(path.join(stagingRoot, filename))) !== sha(bytes)) throw new Error('Written output differs');
    row.outputs[role] = {filename, bytes:bytes.length, sha256:sha(bytes), dimensions:[metadata.width,metadata.height]};
  }
  if (sha(await readFile(path.join(sourceRoot, entry.name))) !== row.sourceSha256) throw new Error('Source changed while encoding');
  frames.push(row);
}
if (sha(await readFile(canonicalPath)) !== sha(Buffer.from(canonicalSource))) throw new Error('Canonical policy changed during encoding');
const evidence = {schemaVersion:1, encoding:media.MEDIA_OPTIMIZATION_VERSION, canonicalPolicy:canonicalPath,
  canonicalPolicySha256:sha(Buffer.from(canonicalSource)), sharpVersion:sharp.versions.sharp,
  originalOptions:media.MEDIA_ORIGINAL_WEBP_OPTIONS, coverOptions:media.MEDIA_COVER_WEBP_OPTIONS,
  thumbnailOptions:media.MEDIA_THUMBNAIL_WEBP_OPTIONS, result:'encoding-and-file-validation-pass',
  visualReview:'pending', uploaded:false, frames};
await writeFile(path.join(stagingRoot,'encoding.json'), JSON.stringify(evidence,null,2)+'\n', {flag:'wx'});
// A failure retains a clearly partial diagnostic directory; expose the package
// only after all eighteen files and the manifest have been verified.
await rename(stagingRoot, outputRoot);
console.log(JSON.stringify({frames:frames.length, sourceBytes:frames.reduce((n,r)=>n+r.sourceBytes,0),
  originalWebpBytes:frames.reduce((n,r)=>n+r.outputs.original.bytes,0), outputRoot}));
