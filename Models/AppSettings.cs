using System.Text.Json.Serialization;

namespace CapsLockShow.Models;

public sealed class AppSettings
{
    [JsonPropertyName("caps_enabled")]
    public bool CapsEnabled { get; set; } = true;

    [JsonPropertyName("num_enabled")]
    public bool NumEnabled { get; set; } = true;

    [JsonPropertyName("scroll_enabled")]
    public bool ScrollEnabled { get; set; } = true;

    [JsonPropertyName("duration_ms")]
    public int DurationMs { get; set; } = 2000;

    [JsonPropertyName("position")]
    public string Position { get; set; } = "bottom_center";

    [JsonPropertyName("theme")]
    public string Theme { get; set; } = "system";

    [JsonPropertyName("startup")]
    public bool Startup { get; set; }

    [JsonPropertyName("hide_directx_fullscreen")]
    public bool HideDirectxFullscreen { get; set; } = true;
}
