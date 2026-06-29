using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using CapsLockShow.Models;
using CapsLockShow.Services;
using MediaColor = System.Windows.Media.Color;
using WpfComboBox = System.Windows.Controls.ComboBox;
using WpfUiApplicationTheme = Wpf.Ui.Appearance.ApplicationTheme;
using WpfUiApplicationThemeManager = Wpf.Ui.Appearance.ApplicationThemeManager;
using WpfUiWindowBackdropType = Wpf.Ui.Controls.WindowBackdropType;
using WpfUiFluentWindow = Wpf.Ui.Controls.FluentWindow;

namespace CapsLockShow.Views;

public partial class SettingsWindow : WpfUiFluentWindow
{
    private AppSettings _settings;
    private bool _syncing;

    public SettingsWindow(AppSettings settings)
    {
        _settings = settings;
        InitializeComponent();
        Sync(settings);
        ShowPage(GeneralItem);
    }

    public event EventHandler? SettingsChanged;
    public event EventHandler<string>? TestFlyoutRequested;
    public event EventHandler<bool>? StartupChangeRequested;

    public void Sync(AppSettings settings)
    {
        _syncing = true;
        _settings = settings;

        CapsEnabledBox.IsChecked = settings.CapsEnabled;
        NumEnabledBox.IsChecked = settings.NumEnabled;
        ScrollEnabledBox.IsChecked = settings.ScrollEnabled;
        FullscreenBox.IsChecked = settings.HideDirectxFullscreen;
        StartupBox.IsChecked = settings.Startup;
        DurationSlider.Value = settings.DurationMs / 100.0;
        DurationText.Text = $"{DurationSlider.Value / 10:0.0} 秒";
        SelectComboByTag(ThemeBox, settings.Theme);
        SelectComboByTag(PositionBox, settings.Position);
        ApplyTheme();

        _syncing = false;
    }

    public void SyncStartup(bool enabled)
    {
        _syncing = true;
        StartupBox.IsChecked = enabled;
        _settings.Startup = enabled;
        _syncing = false;
    }

    private void OnSettingChanged(object sender, RoutedEventArgs e)
    {
        if (_syncing)
        {
            return;
        }

        _settings.CapsEnabled = CapsEnabledBox.IsChecked == true;
        _settings.NumEnabled = NumEnabledBox.IsChecked == true;
        _settings.ScrollEnabled = ScrollEnabledBox.IsChecked == true;
        _settings.HideDirectxFullscreen = FullscreenBox.IsChecked == true;
        SettingsChanged?.Invoke(this, EventArgs.Empty);
    }

    private void OnStartupChanged(object sender, RoutedEventArgs e)
    {
        if (_syncing)
        {
            return;
        }

        StartupChangeRequested?.Invoke(this, StartupBox.IsChecked == true);
    }

    private void OnDurationChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (DurationText is null)
        {
            return;
        }

        DurationText.Text = $"{DurationSlider.Value / 10:0.0} 秒";
        if (_syncing)
        {
            return;
        }

        _settings.DurationMs = (int)Math.Round(DurationSlider.Value) * 100;
        SettingsChanged?.Invoke(this, EventArgs.Empty);
    }

    private void OnThemeChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_syncing || ThemeBox.SelectedItem is not ComboBoxItem item || item.Tag is not string value)
        {
            return;
        }

        _settings.Theme = value;
        ApplyTheme();
        SettingsChanged?.Invoke(this, EventArgs.Empty);
    }

    private void OnPositionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_syncing || PositionBox.SelectedItem is not ComboBoxItem item || item.Tag is not string value)
        {
            return;
        }

        _settings.Position = value;
        SettingsChanged?.Invoke(this, EventArgs.Empty);
    }

    private void OnGeneralClicked(object sender, RoutedEventArgs e) => ShowPage(GeneralItem);
    private void OnAppearanceClicked(object sender, RoutedEventArgs e) => ShowPage(AppearanceItem);
    private void OnAboutClicked(object sender, RoutedEventArgs e) => ShowPage(AboutItem);

    private void ShowPage(object? selectedItem)
    {
        GeneralPage.Visibility = selectedItem == GeneralItem ? Visibility.Visible : Visibility.Collapsed;
        AppearancePage.Visibility = selectedItem == AppearanceItem ? Visibility.Visible : Visibility.Collapsed;
        AboutPage.Visibility = selectedItem == AboutItem ? Visibility.Visible : Visibility.Collapsed;
    }

    private void OnTestCaps(object sender, RoutedEventArgs e) => TestFlyoutRequested?.Invoke(this, "Caps Lock");
    private void OnTestNum(object sender, RoutedEventArgs e) => TestFlyoutRequested?.Invoke(this, "Num Lock");
    private void OnTestScroll(object sender, RoutedEventArgs e) => TestFlyoutRequested?.Invoke(this, "Scroll Lock");

    private static void SelectComboByTag(WpfComboBox comboBox, string tag)
    {
        foreach (var item in comboBox.Items)
        {
            if (item is ComboBoxItem comboBoxItem && string.Equals(comboBoxItem.Tag as string, tag, StringComparison.Ordinal))
            {
                comboBox.SelectedItem = comboBoxItem;
                return;
            }
        }
    }

    private void ApplyTheme()
    {
        var dark = ThemeService.IsDark(_settings.Theme);
        WpfUiApplicationThemeManager.Apply(
            dark ? WpfUiApplicationTheme.Dark : WpfUiApplicationTheme.Light,
            WpfUiWindowBackdropType.Mica,
            updateAccent: true);

        Resources["WindowBackgroundBrush"] = new SolidColorBrush(dark ? MediaColor.FromRgb(32, 32, 32) : MediaColor.FromRgb(247, 247, 247));
        Resources["CardBackgroundBrush"] = new SolidColorBrush(dark ? MediaColor.FromRgb(45, 45, 45) : Colors.White);
        Resources["TextBrush"] = new SolidColorBrush(dark ? MediaColor.FromRgb(243, 243, 243) : MediaColor.FromRgb(31, 31, 31));
        Resources["SubTextBrush"] = new SolidColorBrush(dark ? MediaColor.FromArgb(170, 255, 255, 255) : MediaColor.FromRgb(107, 107, 107));
    }
}
