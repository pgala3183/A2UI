// Node module-resolution hooks so browser modules can be unit-tested in Node.
// In the browser, modules import '/common/x.mjs' and '/shared/x.mjs' (URL paths
// the codelab server mounts). Under `node --test` those paths are mapped to
// common/web/ and to the importing theme's codelabs/<theme>/_shared/ folder.

import { pathToFileURL, fileURLToPath } from 'node:url';
import path from 'node:path';

const COMMON = path.dirname(fileURLToPath(import.meta.url));

export async function resolve(specifier, context, next) {
  if (specifier.startsWith('/common/')) {
    return next(pathToFileURL(path.join(COMMON, specifier.slice('/common/'.length))).href, context);
  }
  if (specifier.startsWith('/shared/') && context.parentURL) {
    const parent = fileURLToPath(context.parentURL);
    const match = parent.match(/^(.*[\\/]codelabs[\\/][^\\/]+)[\\/]/);
    if (match) return next(pathToFileURL(path.join(match[1], '_shared', specifier.slice('/shared/'.length))).href, context);
  }
  return next(specifier, context);
}
