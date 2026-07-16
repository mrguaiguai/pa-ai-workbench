package service

import (
	"strings"
	"testing"

	"github.com/Tencent/WeKnora/internal/mcp"
)

func TestSafeMCPToolOutputRedactsBinaryContent(t *testing.T) {
	output := safeMCPToolOutput([]mcp.ContentItem{
		{Type: "text", Text: "pong"},
		{Type: "image", MimeType: "image/png", Data: "raw-image-data"},
		{Type: "resource", MimeType: "application/json", Data: "raw-resource-data"},
	})

	if !strings.Contains(output, "pong") {
		t.Fatalf("expected text output, got %q", output)
	}
	if !strings.Contains(output, "[Image: image/png]") {
		t.Fatalf("expected image placeholder, got %q", output)
	}
	if !strings.Contains(output, "[Resource: application/json]") {
		t.Fatalf("expected resource placeholder, got %q", output)
	}
	if strings.Contains(output, "raw-image-data") || strings.Contains(output, "raw-resource-data") {
		t.Fatalf("binary content leaked in output: %q", output)
	}
}

func TestTruncateMCPExecutionText(t *testing.T) {
	output := truncateMCPExecutionText("abcdef", 5)
	if output != "ab..." {
		t.Fatalf("unexpected truncated output: %q", output)
	}

	short := truncateMCPExecutionText("abc", 3)
	if short != "abc" {
		t.Fatalf("unexpected short output: %q", short)
	}
}
