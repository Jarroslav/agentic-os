# syntax=docker/dockerfile:1

# Builds the `agentic-os-mcp` stdio MCP server that lives in this repo's mcp/
# directory. The rest of the repo is a Claude Code / Cursor plugin
# marketplace, not a containerised application — this file exists so MCP
# directories that introspect a server by building and running it (Glama, and
# anything else doing the same) can start it in a sandbox and read its tool,
# resource, and prompt schemas. Running the server this way is equivalent to
# `npx -y agentic-os-mcp`; the npm package remains the supported install path
# for end users (see mcp/README.md § Install).
#
# The build context MUST be the repository root, never mcp/, because
# mcp/scripts/build-content.mjs — the only path from plugins/ into the
# published server — needs four things that live outside mcp/:
#   1. plugins/**            the methodology corpus it bundles
#   2. LICENSE and NOTICE    copied into the package (Apache-2.0 requires
#                            both to travel with the distribution)
#   3. a real .git directory  it enumerates content with `git ls-files`, so
#   4. the `git` binary       untracked local debris can never be indexed
# A build scoped to mcp/ fails on all four.
#
#   docker build -t agentic-os-mcp .
#   docker run --rm -i agentic-os-mcp    # stdio: -i is required, -t must NOT be used
#
# Note on .git: it is deliberately NOT excluded in .dockerignore. Point 3
# above means excluding it breaks the build rather than merely slimming the
# context.

FROM node:20-alpine AS build

# git is a build-time-only dependency (point 3 above). The runtime stage does
# not install it: by then the corpus is already baked into dist/content/ and
# enumerated in content-index.json, so the server never shells out to git.
RUN apk add --no-cache git

# Manifests first, on their own layer, so editing a skill or a source file
# does not invalidate the dependency install.
WORKDIR /src/mcp
COPY mcp/package.json mcp/package-lock.json ./
RUN npm ci

# Then the sources the build actually reads. node_modules is excluded via
# .dockerignore, so this COPY merges into the install above instead of
# clobbering it.
WORKDIR /src
COPY LICENSE NOTICE ./
COPY .git ./.git
COPY plugins ./plugins
COPY mcp ./mcp

# COPY writes as root and this stage runs as root, so git's dubious-ownership
# guard is not tripped today. Declared anyway: it costs one cached layer and
# turns an obscure `git ls-files` failure into a non-event if this image is
# ever built under a different user.
RUN git config --global --add safe.directory /src

# build = build:content (index plugins/, copy dist/content/, copy the legal
# files) then build:ts. Pruning in the same layer keeps the dev toolchain
# (typescript, vitest) out of what the runtime stage copies.
WORKDIR /src/mcp
RUN npm run build && npm prune --omit=dev


FROM node:20-alpine

ENV NODE_ENV=production
WORKDIR /app

# dist/ holds both the compiled server and dist/content/ (the bundled
# corpus). content-index.json sits beside it and is the server's entire
# access-control model for that corpus — a path is readable only if it is a
# literal key of this index — so it is not an optional extra.
COPY --from=build /src/mcp/package.json ./package.json
COPY --from=build /src/mcp/node_modules ./node_modules
COPY --from=build /src/mcp/dist ./dist
COPY --from=build /src/mcp/content-index.json ./content-index.json
COPY --from=build /src/mcp/LICENSE /src/mcp/NOTICE ./

# The server only ever reads, and only from its own bundle — but drop root
# regardless, so a container escape has no privileged process to land on.
# `node` is a non-root user the base image already provides.
USER node

# stdio transport: the server speaks JSON-RPC over stdin/stdout and must emit
# nothing else on stdout, so there is no port to EXPOSE and no HEALTHCHECK
# that would not corrupt the stream.
ENTRYPOINT ["node", "dist/index.js"]
