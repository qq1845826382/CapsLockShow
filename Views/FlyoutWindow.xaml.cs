using System;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using CapsLockShow.Models;
using CapsLockShow.Services;
using Forms = System.Windows.Forms;
using MediaColor = System.Windows.Media.Color;
using WpfPoint = System.Windows.Point;

namespace CapsLockShow.Views;

public partial class FlyoutWindow : Window
{
    private readonly System.Windows.Threading.DispatcherTimer _hideTimer = new();
    private AppSettings _settings = new();

    public FlyoutWindow()
    {
        InitializeComponent();
        Opacity = 0;
        _hideTimer.Tick += (_, _) => HideAnimated();
    }

    public void ApplySettings(AppSettings settings)
    {
        _settings = settings;
    }

    public void ShowState(LockKey key, bool isOn)
    {
        _hideTimer.Stop();
        RenderState(key, isOn);

        var target = TargetPosition();
        var offset = target.Y > 80 ? 20 : -20;
        var start = new WpfPoint(target.X, target.Y + offset);

        if (!IsVisible)
        {
            Left = start.X;
            Top = start.Y;
            Opacity = 0;
            Show();
            ApplyNoActivateStyle();
        }

        ActivateTopmostWithoutFocus();
        AnimateTo(target, 1, 180);
        _hideTimer.Interval = TimeSpan.FromMilliseconds(_settings.DurationMs);
        _hideTimer.Start();
    }

    private void HideAnimated()
    {
        _hideTimer.Stop();
        if (!IsVisible)
        {
            return;
        }

        var offset = Top > 80 ? 20 : -20;
        var target = new WpfPoint(Left, Top + offset);
        var storyboard = CreateStoryboard(target, 0, 160);
        storyboard.Completed += (_, _) => Hide();
        storyboard.Begin(this);
    }

    private void AnimateTo(WpfPoint target, double opacity, int durationMs)
    {
        CreateStoryboard(target, opacity, durationMs).Begin(this);
    }

    private Storyboard CreateStoryboard(WpfPoint target, double opacity, int durationMs)
    {
        var easing = new CubicEase { EasingMode = EasingMode.EaseOut };
        var storyboard = new Storyboard();

        var left = new DoubleAnimation(Left, target.X, TimeSpan.FromMilliseconds(durationMs)) { EasingFunction = easing };
        Storyboard.SetTarget(left, this);
        Storyboard.SetTargetProperty(left, new PropertyPath(LeftProperty));
        storyboard.Children.Add(left);

        var top = new DoubleAnimation(Top, target.Y, TimeSpan.FromMilliseconds(durationMs)) { EasingFunction = easing };
        Storyboard.SetTarget(top, this);
        Storyboard.SetTargetProperty(top, new PropertyPath(TopProperty));
        storyboard.Children.Add(top);

        var fade = new DoubleAnimation(Opacity, opacity, TimeSpan.FromMilliseconds(durationMs)) { EasingFunction = easing };
        Storyboard.SetTarget(fade, this);
        Storyboard.SetTargetProperty(fade, new PropertyPath(OpacityProperty));
        storyboard.Children.Add(fade);

        return storyboard;
    }

    private void RenderState(LockKey key, bool isOn)
    {
        var dark = ThemeService.IsDark(_settings.Theme);
        var accent = ThemeService.AccentColor();
        var accentBrush = new SolidColorBrush(accent);
        var muted = dark ? MediaColor.FromArgb(140, 255, 255, 255) : MediaColor.FromArgb(125, 0, 0, 0);
        var mutedBrush = new SolidColorBrush(muted);

        RootBorder.Background = new SolidColorBrush(dark ? MediaColor.FromArgb(232, 32, 32, 32) : MediaColor.FromArgb(235, 252, 252, 252));
        RootBorder.BorderBrush = new SolidColorBrush(dark ? MediaColor.FromArgb(30, 255, 255, 255) : MediaColor.FromArgb(24, 0, 0, 0));
        KeyNameText.Foreground = new SolidColorBrush(dark ? MediaColor.FromRgb(243, 243, 243) : MediaColor.FromRgb(31, 31, 31));
        StatusText.Foreground = mutedBrush;

        KeyIcon.BorderBrush = isOn ? accentBrush : mutedBrush;
        KeyIcon.Background = new SolidColorBrush(MediaColor.FromArgb((byte)(isOn ? 28 : 14), accent.R, accent.G, accent.B));
        SymbolText.Foreground = isOn ? accentBrush : mutedBrush;
        SymbolText.Text = key.Symbol;
        SymbolText.FontSize = key.Name == "Scroll Lock" ? 14 : 15;

        KeyNameText.Text = key.Name;
        StatusText.Text = isOn ? "已开启" : "已关闭";
        Indicator.Background = accentBrush;
        Indicator.Opacity = isOn ? 1 : 0.43;
        Indicator.Width = isOn ? 96 : 52;
    }

    private WpfPoint TargetPosition()
    {
        var cursor = Forms.Cursor.Position;
        var screen = Forms.Screen.FromPoint(cursor);
        var area = screen.WorkingArea;
        const int margin = 24;

        return _settings.Position switch
        {
            "bottom_left" => new WpfPoint(area.Left + margin, area.Bottom - Height - margin),
            "bottom_right" => new WpfPoint(area.Right - Width - margin, area.Bottom - Height - margin),
            "top_center" => new WpfPoint(area.Left + (area.Width - Width) / 2, area.Top + margin),
            _ => new WpfPoint(area.Left + (area.Width - Width) / 2, area.Bottom - Height - margin)
        };
    }

    private void ApplyNoActivateStyle()
    {
        var hwnd = new WindowInteropHelper(this).Handle;
        var style = NativeMethods.GetWindowLong(hwnd, NativeMethods.GWL_EXSTYLE);
        NativeMethods.SetWindowLong(hwnd, NativeMethods.GWL_EXSTYLE, style | NativeMethods.WS_EX_NOACTIVATE | NativeMethods.WS_EX_TOOLWINDOW);
    }

    private void ActivateTopmostWithoutFocus()
    {
        Topmost = false;
        Topmost = true;
    }
}
