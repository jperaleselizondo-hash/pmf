// Offline XanoScript syntax validation for every .xs file under the given directories.
// Uses the validator bundled with @xano/developer-mcp (no network, no Xano access).
//
//   XANO_DEV_MCP_LIB=/path/to/node_modules/@xano/developer-mcp/dist/lib.js \
//     node tests/static/validate_xs.mjs xano/app xano/market xano/research xano/intelligence_validation
import { readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const lib = process.env.XANO_DEV_MCP_LIB;
if (!lib) {
  console.error("Set XANO_DEV_MCP_LIB to @xano/developer-mcp/dist/lib.js");
  process.exit(2);
}
const { validateXanoscript } = await import(pathToFileURL(resolve(lib)).href);

const walk = (dir) => readdirSync(dir).flatMap((name) => {
  const path = join(dir, name);
  return statSync(path).isDirectory() ? walk(path) : path.endsWith(".xs") ? [resolve(path)] : [];
});

const files = process.argv.slice(2).flatMap(walk).sort();
const result = validateXanoscript({ file_paths: files });
const results = result.results ?? [result];
for (const r of results.filter((x) => !x.valid)) {
  console.log(`INVALID ${r.file_path}`);
  for (const e of r.errors ?? []) console.log(`  - ${String(e.message).split("\n")[0]}`);
}
console.log(`${results.filter((x) => x.valid).length} / ${files.length} valid`);
process.exit(results.every((x) => x.valid) ? 0 : 1);
