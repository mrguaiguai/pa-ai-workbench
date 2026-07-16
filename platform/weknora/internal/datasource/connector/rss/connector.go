// Package rss implements a no-credential RSS/Atom data source connector.
package rss

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/xml"
	"fmt"
	"html"
	"io"
	"net/http"
	"net/url"
	"path"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/Tencent/WeKnora/internal/datasource"
	"github.com/Tencent/WeKnora/internal/types"
	secutils "github.com/Tencent/WeKnora/internal/utils"
)

const (
	defaultItemLimit = 20
	maxItemLimit     = 100
)

// Connector syncs items from a public RSS or Atom feed.
type Connector struct {
	httpClient *http.Client
}

// NewConnector returns a new RSS connector.
func NewConnector() *Connector {
	cfg := secutils.DefaultSSRFSafeHTTPClientConfig()
	cfg.Timeout = 20 * time.Second
	return &Connector{httpClient: secutils.NewSSRFSafeHTTPClient(cfg)}
}

// Type returns the connector type identifier.
func (c *Connector) Type() string {
	return types.ConnectorTypeRSS
}

// Validate fetches and parses the configured feed.
func (c *Connector) Validate(ctx context.Context, config *types.DataSourceConfig) error {
	cfg, err := parseConfig(config)
	if err != nil {
		return err
	}
	feed, err := c.fetchFeed(ctx, cfg.FeedURL)
	if err != nil {
		return err
	}
	if len(feed.Items) == 0 {
		return fmt.Errorf("%w: feed contains no items", datasource.ErrInvalidConfig)
	}
	return nil
}

// ListResources returns the configured feed as a single syncable resource.
func (c *Connector) ListResources(ctx context.Context, config *types.DataSourceConfig) ([]types.Resource, error) {
	cfg, err := parseConfig(config)
	if err != nil {
		return nil, err
	}
	feed, err := c.fetchFeed(ctx, cfg.FeedURL)
	if err != nil {
		return nil, err
	}
	return []types.Resource{
		{
			ExternalID: feedID(cfg.FeedURL),
			Name:       firstNonEmpty(feed.Title, "RSS / Atom Feed"),
			Type:       types.ConnectorTypeRSS,
			URL:        cfg.FeedURL,
			ModifiedAt: time.Now().UTC(),
			Metadata: map[string]interface{}{
				"item_count": len(feed.Items),
			},
		},
	}, nil
}

// FetchAll performs a full sync for the configured RSS/Atom feed.
func (c *Connector) FetchAll(
	ctx context.Context,
	config *types.DataSourceConfig,
	resourceIDs []string,
) ([]types.FetchedItem, error) {
	cfg, err := parseConfig(config)
	if err != nil {
		return nil, err
	}
	feedURLs := configuredFeedURLs(cfg, resourceIDs)
	items := make([]types.FetchedItem, 0)
	for _, feedURL := range feedURLs {
		feed, err := c.fetchFeed(ctx, feedURL)
		if err != nil {
			return nil, err
		}
		items = append(items, feed.toFetchedItems(feedURL, cfg.ItemLimit)...)
	}
	return items, nil
}

// FetchIncremental returns current feed items and a time cursor. RSS feeds do
// not provide a portable deletion/change cursor, so the sync service handles
// duplicate external IDs on ingest.
func (c *Connector) FetchIncremental(
	ctx context.Context,
	config *types.DataSourceConfig,
	cursor *types.SyncCursor,
) ([]types.FetchedItem, *types.SyncCursor, error) {
	items, err := c.FetchAll(ctx, config, nil)
	if err != nil {
		return nil, nil, err
	}
	nextCursor := &types.SyncCursor{
		LastSyncTime: time.Now().UTC(),
		ConnectorCursor: map[string]interface{}{
			"mode": "rss_snapshot",
		},
	}
	return items, nextCursor, nil
}

type Config struct {
	FeedURL   string
	ItemLimit int
}

func parseConfig(config *types.DataSourceConfig) (*Config, error) {
	if config == nil {
		return nil, fmt.Errorf("%w: config is nil", datasource.ErrInvalidConfig)
	}
	feedURL := firstNonEmpty(
		stringSetting(config.Settings, "feed_url"),
		stringSetting(config.Settings, "url"),
		firstResourceID(config.ResourceIDs),
	)
	feedURL = strings.TrimSpace(feedURL)
	if feedURL == "" {
		return nil, fmt.Errorf("%w: feed_url is required", datasource.ErrInvalidConfig)
	}
	normalized, err := normalizeFeedURL(feedURL)
	if err != nil {
		return nil, err
	}
	if err := secutils.ValidateURLForSSRF(normalized); err != nil {
		return nil, fmt.Errorf("%w: feed_url failed SSRF validation: %v", datasource.ErrInvalidConfig, err)
	}
	limit := intSetting(config.Settings, "item_limit", defaultItemLimit)
	if limit <= 0 {
		limit = defaultItemLimit
	}
	if limit > maxItemLimit {
		limit = maxItemLimit
	}
	return &Config{FeedURL: normalized, ItemLimit: limit}, nil
}

func (c *Connector) fetchFeed(ctx context.Context, feedURL string) (*parsedFeed, error) {
	if err := secutils.ValidateURLForSSRF(feedURL); err != nil {
		return nil, fmt.Errorf("%w: feed_url failed SSRF validation: %v", datasource.ErrInvalidConfig, err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, feedURL, nil)
	if err != nil {
		return nil, fmt.Errorf("%w: invalid feed request: %v", datasource.ErrInvalidConfig, err)
	}
	req.Header.Set("Accept", "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.1")
	req.Header.Set("User-Agent", "WeKnora-RSS-Connector/1.0")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("%w: fetch feed failed: %v", datasource.ErrFetchFailed, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("%w: feed returned status %d", datasource.ErrFetchFailed, resp.StatusCode)
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, 2<<20))
	if err != nil {
		return nil, fmt.Errorf("%w: read feed failed: %v", datasource.ErrFetchFailed, err)
	}
	feed, err := parseFeed(body)
	if err != nil {
		return nil, err
	}
	return feed, nil
}

type parsedFeed struct {
	Title string
	Items []feedItem
}

type feedItem struct {
	ID        string
	Title     string
	Link      string
	Summary   string
	Content   string
	Published time.Time
	Updated   time.Time
}

func (f *parsedFeed) toFetchedItems(feedURL string, limit int) []types.FetchedItem {
	if limit <= 0 || limit > len(f.Items) {
		limit = len(f.Items)
	}
	out := make([]types.FetchedItem, 0, limit)
	sourceResourceID := feedID(feedURL)
	for _, item := range f.Items[:limit] {
		title := firstNonEmpty(item.Title, "Untitled RSS item")
		updatedAt := firstNonZeroTime(item.Updated, item.Published, time.Now().UTC())
		externalID := firstNonEmpty(item.ID, item.Link, title)
		externalID = itemID(feedURL, externalID)
		out = append(out, types.FetchedItem{
			ExternalID:       externalID,
			Title:            title,
			Content:          []byte(renderMarkdown(title, item.Link, item.Published, item.Summary, item.Content)),
			ContentType:      "text/markdown",
			FileName:         safeFileName(title, externalID),
			URL:              item.Link,
			UpdatedAt:        updatedAt,
			Metadata:         map[string]string{"connector": types.ConnectorTypeRSS, "feed_hash": sourceResourceID},
			SourceResourceID: sourceResourceID,
		})
	}
	return out
}

func parseFeed(body []byte) (*parsedFeed, error) {
	var rss rssFeed
	if err := xml.Unmarshal(body, &rss); err == nil && len(rss.Channel.Items) > 0 {
		items := make([]feedItem, 0, len(rss.Channel.Items))
		for _, item := range rss.Channel.Items {
			items = append(items, feedItem{
				ID:        strings.TrimSpace(item.GUID.Value),
				Title:     cleanupText(item.Title),
				Link:      strings.TrimSpace(item.Link),
				Summary:   cleanupText(item.Description),
				Content:   cleanupText(item.ContentEncoded),
				Published: parseFeedTime(firstNonEmpty(item.PubDate, item.DCDate)),
			})
		}
		return &parsedFeed{Title: cleanupText(rss.Channel.Title), Items: items}, nil
	}

	var atom atomFeed
	if err := xml.Unmarshal(body, &atom); err == nil && len(atom.Entries) > 0 {
		items := make([]feedItem, 0, len(atom.Entries))
		for _, entry := range atom.Entries {
			items = append(items, feedItem{
				ID:        strings.TrimSpace(entry.ID),
				Title:     cleanupText(entry.Title),
				Link:      atomLinkHref(entry.Links),
				Summary:   cleanupText(entry.Summary),
				Content:   cleanupText(entry.Content),
				Published: parseFeedTime(entry.Published),
				Updated:   parseFeedTime(entry.Updated),
			})
		}
		return &parsedFeed{Title: cleanupText(atom.Title), Items: items}, nil
	}

	return nil, fmt.Errorf("%w: unsupported RSS/Atom feed or empty item list", datasource.ErrInvalidConfig)
}

type rssFeed struct {
	Channel rssChannel `xml:"channel"`
}

type rssChannel struct {
	Title string    `xml:"title"`
	Items []rssItem `xml:"item"`
}

type rssItem struct {
	Title          string  `xml:"title"`
	Link           string  `xml:"link"`
	GUID           rssGUID `xml:"guid"`
	Description    string  `xml:"description"`
	ContentEncoded string  `xml:"encoded"`
	PubDate        string  `xml:"pubDate"`
	DCDate         string  `xml:"date"`
}

type rssGUID struct {
	Value string `xml:",chardata"`
}

type atomFeed struct {
	Title   string      `xml:"title"`
	Entries []atomEntry `xml:"entry"`
}

type atomEntry struct {
	ID        string     `xml:"id"`
	Title     string     `xml:"title"`
	Links     []atomLink `xml:"link"`
	Summary   string     `xml:"summary"`
	Content   string     `xml:"content"`
	Published string     `xml:"published"`
	Updated   string     `xml:"updated"`
}

type atomLink struct {
	Href string `xml:"href,attr"`
	Rel  string `xml:"rel,attr"`
}

func normalizeFeedURL(raw string) (string, error) {
	parsed, err := url.Parse(raw)
	if err != nil {
		return "", fmt.Errorf("%w: invalid feed_url: %v", datasource.ErrInvalidConfig, err)
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return "", fmt.Errorf("%w: feed_url must use http or https", datasource.ErrInvalidConfig)
	}
	if parsed.Hostname() == "" {
		return "", fmt.Errorf("%w: feed_url host is required", datasource.ErrInvalidConfig)
	}
	return parsed.String(), nil
}

func configuredFeedURLs(cfg *Config, resourceIDs []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, candidate := range append(resourceIDs, cfg.FeedURL) {
		normalized, err := normalizeFeedURL(strings.TrimSpace(candidate))
		if err != nil || seen[normalized] {
			continue
		}
		out = append(out, normalized)
		seen[normalized] = true
	}
	return out
}

func stringSetting(settings map[string]interface{}, key string) string {
	if settings == nil {
		return ""
	}
	value, ok := settings[key]
	if !ok || value == nil {
		return ""
	}
	switch v := value.(type) {
	case string:
		return v
	default:
		return fmt.Sprint(v)
	}
}

func intSetting(settings map[string]interface{}, key string, fallback int) int {
	if settings == nil {
		return fallback
	}
	value, ok := settings[key]
	if !ok || value == nil {
		return fallback
	}
	switch v := value.(type) {
	case int:
		return v
	case int64:
		return int(v)
	case float64:
		return int(v)
	case string:
		parsed, err := strconv.Atoi(strings.TrimSpace(v))
		if err == nil {
			return parsed
		}
	}
	return fallback
}

func firstResourceID(resourceIDs []string) string {
	for _, id := range resourceIDs {
		if strings.TrimSpace(id) != "" {
			return id
		}
	}
	return ""
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func firstNonZeroTime(values ...time.Time) time.Time {
	for _, value := range values {
		if !value.IsZero() {
			return value
		}
	}
	return time.Time{}
}

func parseFeedTime(raw string) time.Time {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return time.Time{}
	}
	layouts := []string{
		time.RFC3339,
		time.RFC3339Nano,
		time.RFC1123Z,
		time.RFC1123,
		time.RFC822Z,
		time.RFC822,
		"Mon, 02 Jan 2006 15:04:05 MST",
		"2006-01-02T15:04:05Z07:00",
	}
	for _, layout := range layouts {
		if parsed, err := time.Parse(layout, raw); err == nil {
			return parsed.UTC()
		}
	}
	return time.Time{}
}

func atomLinkHref(links []atomLink) string {
	for _, link := range links {
		if strings.TrimSpace(link.Rel) == "" || link.Rel == "alternate" {
			return strings.TrimSpace(link.Href)
		}
	}
	if len(links) > 0 {
		return strings.TrimSpace(links[0].Href)
	}
	return ""
}

func cleanupText(raw string) string {
	raw = html.UnescapeString(strings.TrimSpace(raw))
	raw = strings.ReplaceAll(raw, "\r\n", "\n")
	raw = strings.ReplaceAll(raw, "\r", "\n")
	return strings.TrimSpace(raw)
}

var tagPattern = regexp.MustCompile(`<[^>]+>`)

func renderMarkdown(title, link string, published time.Time, summary, content string) string {
	var b strings.Builder
	b.WriteString("# ")
	b.WriteString(title)
	b.WriteString("\n\n")
	if link != "" {
		b.WriteString("Source: ")
		b.WriteString(link)
		b.WriteString("\n\n")
	}
	if !published.IsZero() {
		b.WriteString("Published: ")
		b.WriteString(published.Format(time.RFC3339))
		b.WriteString("\n\n")
	}
	body := firstNonEmpty(content, summary)
	body = strings.TrimSpace(tagPattern.ReplaceAllString(body, " "))
	body = strings.Join(strings.Fields(body), " ")
	if body != "" {
		b.WriteString(body)
		b.WriteString("\n")
	}
	return b.String()
}

func feedID(feedURL string) string {
	sum := sha256.Sum256([]byte(feedURL))
	return "rss-feed-" + hex.EncodeToString(sum[:])[:16]
}

func itemID(feedURL, itemKey string) string {
	sum := sha256.Sum256([]byte(feedURL + "\x00" + itemKey))
	return "rss-item-" + hex.EncodeToString(sum[:])[:24]
}

func safeFileName(title, externalID string) string {
	name := strings.ToLower(title)
	name = tagPattern.ReplaceAllString(name, "")
	name = strings.Map(func(r rune) rune {
		if r >= 'a' && r <= 'z' || r >= '0' && r <= '9' {
			return r
		}
		if r == '-' || r == '_' || r == ' ' {
			return r
		}
		return '-'
	}, name)
	name = strings.Join(strings.Fields(name), "-")
	name = strings.Trim(name, "-_ ")
	if name == "" {
		name = externalID
	}
	if ext := path.Ext(name); ext == ".md" {
		return name
	}
	if len(name) > 80 {
		name = name[:80]
	}
	return name + ".md"
}
