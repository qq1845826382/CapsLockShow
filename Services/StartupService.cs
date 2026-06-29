using System;
using Microsoft.Win32;

namespace CapsLockShow.Services;

public sealed class StartupService
{
    private const string RunKeyPath = @"Software\Microsoft\Windows\CurrentVersion\Run";

    public bool IsEnabled()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, false);
            return string.Equals(key?.GetValue(AppConstants.StartupValueName) as string, StartupCommand, StringComparison.Ordinal);
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
    }

    public void SetEnabled(bool enabled)
    {
        using var key = Registry.CurrentUser.OpenSubKey(RunKeyPath, true)
                        ?? Registry.CurrentUser.CreateSubKey(RunKeyPath, true);

        if (enabled)
        {
            key.SetValue(AppConstants.StartupValueName, StartupCommand, RegistryValueKind.String);
        }
        else
        {
            key.DeleteValue(AppConstants.StartupValueName, false);
        }
    }

    private static string StartupCommand => $"\"{Environment.ProcessPath}\"";
}
