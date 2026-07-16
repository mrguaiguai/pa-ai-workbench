# Third-Party Notices

This file is the repository-level attribution index for PA AI Workbench. It
does not replace the full license texts shipped with third-party components.

## Controlled WeKnora source

PA AI Workbench includes a controlled copy of WeKnora under
[`platform/weknora`](platform/weknora).

| Field | Recorded value |
| --- | --- |
| Project | WeKnora |
| Copyright notice | Copyright (C) 2025 Tencent. All rights reserved. |
| Upstream repository | <https://github.com/Tencent/WeKnora> |
| Imported version marker | `0.6.0` |
| Official `v0.6.0` tag commit | `b0094ff47917b5abece91acff4c7e16710368f2c` |
| Reconstructed upstream source anchor | `482686d17ee89aefea54cf05bf843c04d152db27` |
| Local native import commit | `42a6f0ac810dd04a64a6b0999b06554ac76a5e0b` |
| Coherent PA/native baseline | `e7b258c61d56bd44ce477ef29cf761d8ab07cdfc` |
| License and bundled notices | [`platform/weknora/LICENSE`](platform/weknora/LICENSE) |
| Provenance record | [`platform/weknora/UPSTREAM.md`](platform/weknora/UPSTREAM.md) |
| PA modification ledger | [`platform/weknora/PA_PATCHES.md`](platform/weknora/PA_PATCHES.md) |

The imported `VERSION` value identifies the release marker but not an exact
source tree. Read the provenance record before synchronizing or redistributing
the controlled native source: the local import is not tree-identical to the
official `v0.6.0` tag or to the reconstructed source anchor.

## WeKnora MCP server

The standalone source under `platform/weknora/mcp-server` carries an MIT
license with copyright attributed to the WeKnora Team. The authoritative text
is [`platform/weknora/mcp-server/LICENSE`](platform/weknora/mcp-server/LICENSE).

## Dependency manifests

Go, Python, Node.js, container, and system dependencies are declared by the
repository manifests and lockfiles. Each dependency remains subject to its own
license and notice requirements. The long-form WeKnora license bundles the
third-party notices supplied with the imported native platform; this index
does not claim to be a newly generated legal or software-bill-of-materials
audit. Release and clean-clone acceptance must preserve all component license
files and may generate a release-specific dependency/SBOM inventory without
rewriting this provenance record.
