package handler

import (
	"fmt"
	"net/url"
	"os"
	"strings"

	secutils "github.com/Tencent/WeKnora/internal/utils"
)

const mcpSSRFAllowlistEnv = "WEKNORA_MCP_SSRF_ALLOWLIST"

// validateMCPServiceURLForSSRF keeps the global SSRF policy intact while
// allowing operators to opt in to exact local MCP endpoints for development
// validation. The allowlist is intentionally URL-exact rather than host-wide.
func validateMCPServiceURLForSSRF(rawURL string) error {
	err := secutils.ValidateURLForSSRF(rawURL)
	if err == nil {
		return nil
	}
	if isExplicitlyAllowedMCPURL(rawURL) {
		return nil
	}
	return err
}

func formatMCPServiceSSRFError(rawURL string, err error) string {
	base := secutils.FormatSSRFError("MCP service URL", rawURL, err)
	return base + fmt.Sprintf(
		"。仅用于本机 MCP 开发验证时，也可在 %s 中加入完整精确 URL；该变量不支持通配，且只作用于 MCP 服务 URL。",
		mcpSSRFAllowlistEnv,
	)
}

func isExplicitlyAllowedMCPURL(rawURL string) bool {
	normalizedRaw, err := normalizeMCPAllowlistURL(rawURL)
	if err != nil {
		return false
	}
	for _, entry := range strings.Split(os.Getenv(mcpSSRFAllowlistEnv), ",") {
		normalizedEntry, err := normalizeMCPAllowlistURL(entry)
		if err == nil && normalizedEntry == normalizedRaw {
			return true
		}
	}
	return false
}

func normalizeMCPAllowlistURL(rawURL string) (string, error) {
	rawURL = strings.TrimSpace(rawURL)
	if rawURL == "" || !strings.Contains(rawURL, "://") {
		return "", fmt.Errorf("MCP allowlist entry must be an absolute URL")
	}

	parsed, err := url.Parse(rawURL)
	if err != nil {
		return "", err
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return "", fmt.Errorf("MCP allowlist entry must use http or https")
	}
	if parsed.Hostname() == "" {
		return "", fmt.Errorf("MCP allowlist entry must include a host")
	}
	if parsed.User != nil {
		return "", fmt.Errorf("MCP allowlist entry must not include user info")
	}

	parsed.Scheme = strings.ToLower(parsed.Scheme)
	parsed.Host = strings.ToLower(parsed.Host)
	parsed.Fragment = ""
	if parsed.Path == "" {
		parsed.Path = "/"
	}
	return parsed.String(), nil
}
