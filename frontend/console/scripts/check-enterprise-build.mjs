import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";

const root = new URL("../dist/enterprise/", import.meta.url);
const entries = await readdir(root);
assert.deepEqual(entries.sort(), ["assets", "favicon.svg", "index.html"], "Enterprise build must not publish sample reports or arbitrary public files");
assert.match(await readFile(new URL("index.html", root), "utf8"), /<div id="root"><\/div>/);
console.log("Enterprise build contains application assets only; no bundled reports.");
