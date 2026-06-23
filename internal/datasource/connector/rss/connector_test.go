package rss

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/Tencent/WeKnora/internal/types"
	secutils "github.com/Tencent/WeKnora/internal/utils"
)

func TestConnectorType(t *testing.T) {
	if got := NewConnector().Type(); got != types.ConnectorTypeRSS {
		t.Fatalf("Type() = %q, want %q", got, types.ConnectorTypeRSS)
	}
}

func TestValidateAndFetchAllRSS(t *testing.T) {
	server := newFeedServer(t, rssFixture)
	cfg := rssConfig(server.URL + "/rss")

	connector := NewConnector()
	if err := connector.Validate(context.Background(), cfg); err != nil {
		t.Fatalf("Validate() error = %v", err)
	}

	resources, err := connector.ListResources(context.Background(), cfg)
	if err != nil {
		t.Fatalf("ListResources() error = %v", err)
	}
	if len(resources) != 1 {
		t.Fatalf("ListResources() len = %d, want 1", len(resources))
	}
	if resources[0].ExternalID == "" || resources[0].Name != "WeKnora RSS Smoke" {
		t.Fatalf("unexpected resource: %+v", resources[0])
	}

	items, err := connector.FetchAll(context.Background(), cfg, cfg.ResourceIDs)
	if err != nil {
		t.Fatalf("FetchAll() error = %v", err)
	}
	if len(items) != 1 {
		t.Fatalf("FetchAll() len = %d, want 1", len(items))
	}
	item := items[0]
	if item.ExternalID == "" || item.SourceResourceID == "" {
		t.Fatalf("expected stable IDs, got item=%+v", item)
	}
	if item.ContentType != "text/markdown" || !strings.Contains(string(item.Content), "Source: https://example.com/a") {
		t.Fatalf("unexpected markdown item: %+v content=%s", item, item.Content)
	}
}

func TestFetchAllAtom(t *testing.T) {
	server := newFeedServer(t, atomFixture)
	cfg := rssConfig(server.URL + "/atom")

	items, err := NewConnector().FetchAll(context.Background(), cfg, nil)
	if err != nil {
		t.Fatalf("FetchAll() error = %v", err)
	}
	if len(items) != 1 {
		t.Fatalf("FetchAll() len = %d, want 1", len(items))
	}
	if !strings.Contains(string(items[0].Content), "Atom body") {
		t.Fatalf("expected atom body in markdown, got %s", items[0].Content)
	}
}

func TestValidateRejectsMissingFeedURL(t *testing.T) {
	err := NewConnector().Validate(context.Background(), &types.DataSourceConfig{
		Type: types.ConnectorTypeRSS,
	})
	if err == nil {
		t.Fatal("Validate() error = nil, want missing feed_url error")
	}
}

func newFeedServer(t *testing.T, body string) *httptest.Server {
	t.Helper()
	secutils.SetSSRFWhitelistFromRaw("127.0.0.1,localhost")
	t.Cleanup(secutils.ResetSSRFWhitelistForTest)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/xml")
		_, _ = w.Write([]byte(body))
	}))
	t.Cleanup(server.Close)
	return server
}

func rssConfig(feedURL string) *types.DataSourceConfig {
	return &types.DataSourceConfig{
		Type:        types.ConnectorTypeRSS,
		ResourceIDs: []string{feedURL},
		Settings: map[string]interface{}{
			"feed_url":   feedURL,
			"item_limit": 1,
		},
	}
}

const rssFixture = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>WeKnora RSS Smoke</title>
    <item>
      <title>First Item</title>
      <link>https://example.com/a</link>
      <guid>first-guid</guid>
      <pubDate>Mon, 24 Jun 2026 10:00:00 +0800</pubDate>
      <description><![CDATA[<p>First body</p>]]></description>
    </item>
  </channel>
</rss>`

const atomFixture = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>WeKnora Atom Smoke</title>
  <entry>
    <id>tag:example.com,2026:item</id>
    <title>Atom Item</title>
    <link href="https://example.com/atom-item" rel="alternate"/>
    <updated>2026-06-24T02:00:00Z</updated>
    <content type="html"><![CDATA[<p>Atom body</p>]]></content>
  </entry>
</feed>`
