// The app imports through the "@/..." alias, which Next resolves at build time.
// The compiled tests run under plain Node, so map "@/x" onto the compiled output.
const Module = require("node:module");
const path = require("node:path");

const buildRoot = path.resolve(__dirname, "../../.test-build");
const resolve = Module._resolveFilename;

Module._resolveFilename = function resolveAlias(request, ...rest) {
  if (request.startsWith("@/")) {
    return resolve.call(this, path.join(buildRoot, request.slice(2)), ...rest);
  }
  return resolve.call(this, request, ...rest);
};
