# WNID-P4-01 Web Search Provider Setup And Test

> Date: 2026-06-25
>
> Task: `WNID-P4-01`
>
> Evidence type: native Go test + Docker runtime + live API + live browser + audit + masked provider test
>
> Decision: PASS

## Scope

This task completed the native Web Search provider setup foundation for WNID.
It does not claim the final Web Search AgentQA PASS; `WNID-P4-02` must still
prove a native AgentQA run with `web_search_enabled=true` and traceable web
references.

## Native Source Audit

WeKnora native Web Search already exposes the required provider management
surface:

| Native surface | Evidence |
| --- | --- |
| Provider types | `GET /api/v1/web-search-providers/types`; includes `duckduckgo` as a no-credential provider. |
| Provider CRUD | `POST/GET/PUT/DELETE /api/v1/web-search-providers`; Admin mutations, Viewer reads. |
| Credential subresource | `PUT /api/v1/web-search-providers/{id}/credentials`; `DELETE /credentials/{field}`; response uses masked metadata. |
| Saved provider test | `POST /api/v1/web-search-providers/{id}/test`; performs an external sample search. |
| Raw provider test | `POST /api/v1/web-search-providers/test`; tests unsaved parameters without persistence. |
| Secret boundary | `dto.NewWebSearchProviderResponse` omits the credential value; PA additionally returns parameter status rather than raw base/proxy URL values. |
| Update safety | `PUT /api/v1/web-search-providers/{id}` now preserves existing parameters and default flag when PA omits those fields, preventing name-only updates from clearing stored provider configuration. |
| AgentQA dependency | Native search pipeline calls Web Search only when `web_search_enabled` is true and a provider id is selected. |

## PA Changes

PA now exposes a confirmed native provider setup workflow:

| PA surface | Status | Notes |
| --- | --- | --- |
| Adapter | complete | Added safe create/update/delete, credential update/clear, raw test, saved test wrappers in `WeKnoraApiBackend`. |
| BFF | complete | Added confirmation-gated provider setup/test APIs under `/api/web-search/native/providers*`. |
| Audit | complete | Provider mutations and tests record `NativeMutationAudit` with `capability=web_search`. |
| Masking | complete | Responses expose credential counts/status only; raw `api_key`, raw provider payload, raw base URL, and raw proxy URL are not returned. |
| Dialogue UI | complete | `#/dialogue` shows Web Search provider readiness and DuckDuckGo setup/test controls. |

## Live Evidence

Native validation:

```text
docker run --rm -v /Users/mac/Downloads/WeKnora-main:/workspace -v /private/tmp/pa-go-mod-cache:/go/pkg/mod -w /workspace golang:1.26.0 go test ./internal/handler ./internal/application/service -run 'TestWebSearchProviderResponse_OmitsSecrets|TestWebSearchProviderResponse_NilSafe' -count=1
docker compose up -d --no-deps --build app
```

PA checker command:

```text
backend/.venv/bin/python backend/scripts/check_weknora_native_intelligent_dialogue_web_search_provider_setup.py
```

Output:

```text
WeKnora native intelligent dialogue Web Search provider setup
- decision: PASS
- task: WNID-P4-01
- evidence_type: live_api + live_browser + audit + masked_provider_test
- api: provider=duckduckgo provider_id=80cc11c4-c392-4e67-a7a5-fad85cbf6451 created=false ready_provider_count=1 saved_test=live success=true
- blocker: none
- browser: route=dialogue web_search_provider_setup=visible markers=8 hidden_advanced_panel=false
```

The checker:

- started temporary PA backend/frontend services;
- verified native provider type and configured provider surfaces through PA;
- confirmed bad-token provider setup is blocked;
- created or reused a no-credential `duckduckgo` provider through confirmed PA API;
- ran the saved native provider test successfully;
- verified at least one `web_search` native audit event;
- opened `#/dialogue` in headless Chrome and proved the Web Search provider
  setup panel is visible outside any hidden advanced panel.

## Current Truth

`WNID-P4-01` is complete. A real no-credential native DuckDuckGo provider is
configured and saved-provider test passed.

`WNID-P4-02` remains open. The next task must run native AgentQA with
`web_search_enabled=true`, select this provider id or the default provider,
and prove traceable web references with provider/title/snippet/rank or the
closest native reference shape.
