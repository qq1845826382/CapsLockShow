using System;
using System.Windows.Media;
using Microsoft.Win32;
using MediaColor = System.Windows.Media.Color;

namespace CapsLockShow.Services;

public static class ThemeService
{
    public static bool IsDark(string theme)
    {
        return theme switch
        {
            "dark" => true,
            "light" => false,
            _ => SystemThemeIsDark()
        };
    }

    public static MediaColor AccentColor()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\DWM", false);
            if (key?.GetValue("ColorizationColor") is int raw)
            {
                return MediaColor.FromRgb((byte)((raw >> 16) & 0xff), (byte)((raw >> 8) & 0xff), (byte)(raw & 0xff));
            }
        }
        catch (UnauthorizedAccessException)
        {
        }

        return MediaColor.FromRgb(0x00, 0x78, 0xd4);
    }

    private static bool SystemThemeIsDark()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", false);
            return key?.GetValue("AppsUseLightTheme") is int value && value == 0;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
    }
}
