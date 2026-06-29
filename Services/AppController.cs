using System;
using System.Drawing;
using System.IO;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media.Imaging;
using CapsLockShow.Models;
using CapsLockShow.Views;
using DrawingIcon = System.Drawing.Icon;
using WpfApplication = System.Windows.Application;
using WpfMessageBox = System.Windows.MessageBox;

namespace CapsLockShow.Services;

public sealed class AppController : IDisposable
{
    private readonly WpfApplication _application;
    private readonly StartupService _startupService = new();
    private readonly SettingsService _settingsService;
    private readonly KeyboardHookService _keyboardHook = new();
    private readonly TrayService _trayService;
    private readonly FlyoutWindow _flyoutWindow;
    private readonly SettingsWindow _settingsWindow;
    private AppSettings _settings;

    public AppController(WpfApplication application)
    {
        _application = application;
        _settingsService = new SettingsService(_startupService);
        _settings = _settingsService.Load();

        _trayService = new TrayService(LoadTrayIcon());
        _flyoutWindow = new FlyoutWindow();
        _settingsWindow = new SettingsWindow(_settings)
        {
            Icon = new BitmapImage(new Uri("pack://application:,,,/Resources/App.ico"))
        };
        _flyoutWindow.ApplySettings(_settings);

        _keyboardHook.KeyReleased += OnKeyReleased;
        _trayService.OpenSettingsRequested += (_, _) => OpenSettings();
        _trayService.TestFlyoutRequested += (_, keyName) => TestFlyout(keyName);
        _trayService.StartupChanged += (_, enabled) => SetStartup(enabled);
        _settingsWindow.SettingsChanged += (_, _) => SaveSettings();
        _settingsWindow.TestFlyoutRequested += (_, keyName) => TestFlyout(keyName);
        _settingsWindow.StartupChangeRequested += (_, enabled) => SetStartup(enabled);
        _settingsWindow.Closing += (_, args) =>
        {
            args.Cancel = true;
            _settingsWindow.Hide();
        };
    }

    public void Start()
    {
        _trayService.SyncStartup(_settings.Startup);
        _keyboardHook.Start();
        _ = ShowStartupFeedbackAsync();
    }

    public void Dispose()
    {
        _keyboardHook.Dispose();
        _trayService.Dispose();
    }

    private async Task ShowStartupFeedbackAsync()
    {
        await Task.Delay(650);
        _application.Dispatcher.Invoke(() =>
        {
            if (ShouldSuppressFlyout())
            {
                return;
            }

            ShowFlyout(LockKeys.CapsLock);
        });
    }

    private void OnKeyReleased(object? sender, int virtualKey)
    {
        _application.Dispatcher.InvokeAsync(async () =>
        {
            await Task.Delay(20);
            var key = LockKeys.FromVirtualKey(virtualKey);
            if (key is null || !key.IsEnabled(_settings) || ShouldSuppressFlyout())
            {
                return;
            }

            ShowFlyout(key);
        });
    }

    private void OpenSettings()
    {
        _settingsWindow.Sync(_settings);
        _settingsWindow.Show();
        _settingsWindow.Activate();
    }

    private void TestFlyout(string keyName)
    {
        var key = LockKeys.FromName(keyName);
        if (key is not null)
        {
            ShowFlyout(key);
        }
    }

    private void ShowFlyout(LockKey key)
    {
        _flyoutWindow.ApplySettings(_settings);
        _flyoutWindow.ShowState(key, KeyboardState.IsToggled(key.VirtualKey));
    }

    private void SaveSettings()
    {
        _settingsService.Save(_settings);
        _trayService.SyncStartup(_settings.Startup);
        _flyoutWindow.ApplySettings(_settings);
    }

    private void SetStartup(bool enabled)
    {
        try
        {
            _startupService.SetEnabled(enabled);
            _settings.Startup = enabled;
            SaveSettings();
            _settingsWindow.SyncStartup(enabled);
        }
        catch (Exception ex) when (ex is UnauthorizedAccessException or IOException)
        {
            WpfMessageBox.Show($"无法更新开机启动设置：{ex.Message}", AppConstants.AppName, MessageBoxButton.OK, MessageBoxImage.Warning);
            _trayService.SyncStartup(_settings.Startup);
            _settingsWindow.SyncStartup(_settings.Startup);
        }
    }

    private bool ShouldSuppressFlyout()
    {
        return _settings.HideDirectxFullscreen && FullscreenService.IsDirectxFullscreen();
    }

    private static DrawingIcon LoadTrayIcon()
    {
        var resource = WpfApplication.GetResourceStream(new Uri("pack://application:,,,/Resources/App.ico"));
        if (resource is null)
        {
            return SystemIcons.Application;
        }

        return new DrawingIcon(resource.Stream);
    }
}
