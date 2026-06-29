package handler

import "testing"

func TestValidateMCPServiceURLForSSRFExactAllowlist(t *testing.T) {
	t.Setenv(mcpSSRFAllowlistEnv, "http://host.docker.internal:8765/mcp")

	if err := validateMCPServiceURLForSSRF("http://host.docker.internal:8765/mcp"); err != nil {
		t.Fatalf("expected exact allowlisted local MCP URL to pass, got %v", err)
	}
}

func TestValidateMCPServiceURLForSSRFDeniesNearMisses(t *testing.T) {
	t.Setenv(mcpSSRFAllowlistEnv, "http://host.docker.internal:8765/mcp")

	for _, rawURL := range []string{
		"http://host.docker.internal:8766/mcp",
		"http://host.docker.internal:8765/admin",
		"http://127.0.0.1:8765/mcp",
	} {
		if err := validateMCPServiceURLForSSRF(rawURL); err == nil {
			t.Fatalf("expected non-allowlisted MCP URL %q to fail", rawURL)
		}
	}
}

func TestNormalizeMCPAllowlistURLRejectsUnsafeForms(t *testing.T) {
	for _, rawURL := range []string{
		"host.docker.internal:8765/mcp",
		"file:///tmp/mcp.sock",
		"http://user:pass@host.docker.internal:8765/mcp",
	} {
		if _, err := normalizeMCPAllowlistURL(rawURL); err == nil {
			t.Fatalf("expected unsafe allowlist entry %q to fail", rawURL)
		}
	}
}
