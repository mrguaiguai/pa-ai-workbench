package rerank

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestAliyunRerankerQwen3CompatibleAPI(t *testing.T) {
	var gotPath string
	var gotBody map[string]interface{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		if r.Header.Get("Authorization") != "Bearer test-key" {
			t.Fatalf("authorization header not set")
		}
		if err := json.NewDecoder(r.Body).Decode(&gotBody); err != nil {
			t.Fatalf("decode request body: %v", err)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"id":"req-1",
			"model":"qwen3-rerank",
			"results":[{"index":1,"relevance_score":0.91}]
		}`))
	}))
	defer server.Close()

	reranker, err := NewAliyunReranker(&RerankerConfig{
		APIKey:    "test-key",
		BaseURL:   server.URL + "/compatible-api/v1",
		ModelName: "qwen3-rerank",
	})
	if err != nil {
		t.Fatalf("NewAliyunReranker: %v", err)
	}

	results, err := reranker.Rerank(context.Background(), "ping", []string{"low", "pong"})
	if err != nil {
		t.Fatalf("Rerank: %v", err)
	}
	if gotPath != "/compatible-api/v1/reranks" {
		t.Fatalf("path = %q, want compatible reranks path", gotPath)
	}
	if gotBody["model"] != "qwen3-rerank" || gotBody["query"] != "ping" {
		t.Fatalf("unexpected request body: %#v", gotBody)
	}
	if gotBody["top_n"].(float64) != 2 {
		t.Fatalf("top_n = %#v, want 2", gotBody["top_n"])
	}
	if len(results) != 1 || results[0].Index != 1 || results[0].RelevanceScore != 0.91 {
		t.Fatalf("unexpected results: %#v", results)
	}
}

func TestAliyunRerankerLegacyDashScopeAPI(t *testing.T) {
	var gotPath string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"output":{
				"results":[
					{"index":0,"relevance_score":0.88,"document":{"text":"pong"}}
				]
			}
		}`))
	}))
	defer server.Close()

	reranker, err := NewAliyunReranker(&RerankerConfig{
		APIKey:    "test-key",
		BaseURL:   server.URL + "/api/v1/services/rerank/text-rerank/text-rerank",
		ModelName: "gte-rerank-v2",
	})
	if err != nil {
		t.Fatalf("NewAliyunReranker: %v", err)
	}

	results, err := reranker.Rerank(context.Background(), "ping", []string{"pong"})
	if err != nil {
		t.Fatalf("Rerank: %v", err)
	}
	if gotPath != "/api/v1/services/rerank/text-rerank/text-rerank" {
		t.Fatalf("path = %q, want legacy path", gotPath)
	}
	if len(results) != 1 || results[0].Document.Text != "pong" {
		t.Fatalf("unexpected results: %#v", results)
	}
}
