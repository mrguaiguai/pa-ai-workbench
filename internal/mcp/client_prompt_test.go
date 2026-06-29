package mcp

import (
	"strings"
	"testing"

	protocol "github.com/mark3labs/mcp-go/mcp"
)

func TestSafeMCPPromptMessageRedactsBinaryContent(t *testing.T) {
	message := safeMCPPromptMessage(protocol.PromptMessage{
		Role: protocol.RoleUser,
		Content: protocol.ImageContent{
			Type:     "image",
			Data:     "raw-image-data",
			MIMEType: "image/png",
		},
	})

	if message.Role != "user" {
		t.Fatalf("unexpected role: %q", message.Role)
	}
	if message.ContentType != "image" || message.MimeType != "image/png" {
		t.Fatalf("unexpected content summary: %#v", message)
	}
	if message.Text != "" || strings.Contains(message.Text, "raw-image-data") {
		t.Fatalf("binary prompt content leaked: %#v", message)
	}
}

func TestTruncateMCPPromptText(t *testing.T) {
	output := truncateMCPPromptText("abcdef", 5)
	if output != "ab..." {
		t.Fatalf("unexpected truncated prompt: %q", output)
	}

	short := truncateMCPPromptText("abc", 3)
	if short != "abc" {
		t.Fatalf("unexpected short prompt: %q", short)
	}
}
