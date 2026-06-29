using System;
using System.IO;
using System.Text.Json;
using CapsLockShow.Models;

namespace CapsLockShow.Services;

public sealed class SettingsService
{
    private readonly StartupService _startupService;
    private readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = true
    };

    public SettingsService(StartupService startupService)
    {
        _startupService = startupService;
    }

    public string ConfigPath => Path.Combine(AppDataDirectory, "config.json");

    private static string AppDataDirectory
    {
        get
        {
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            return Path.Combine(appData, AppConstants.AppName);
        }
    }

    public AppSettings Load()
    {
        AppSettings settings;

        try
        {
            if (!File.Exists(ConfigPath))
            {
                settings = new AppSettings();
            }
            else
            {
                var json = File.ReadAllText(ConfigPath);
                settings = JsonSerializer.Deserialize<AppSettings>(json, _jsonOptions) ?? new AppSettings();
            }
        }
        catch (IOException)
        {
            settings = new AppSettings();
        }
        catch (JsonException)
        {
            settings = new AppSettings();
        }
        catch (UnauthorizedAccessException)
        {
            settings = new AppSettings();
        }

        Normalize(settings);
        settings.Startup = _startupService.IsEnabled();
        return settings;
    }

    public void Save(AppSettings settings)
    {
        Normalize(settings);
        Directory.CreateDirectory(AppDataDirectory);
        File.WriteAllText(ConfigPath, JsonSerializer.Serialize(settings, _jsonOptions));
    }

    private static void Normalize(AppSettings settings)
    {
        settings.DurationMs = Math.Clamp(settings.DurationMs, 500, 5000);

        if (settings.Position is not ("bottom_center" or "bottom_left" or "bottom_right" or "top_center"))
        {
            settings.Position = "bottom_center";
        }

        if (settings.Theme is not ("system" or "light" or "dark"))
        {
            settings.Theme = "system";
        }
    }
}
