using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using CapsLockShow.Models;
using CapsLockShow.Services;
using Forms = System.Windows.Forms;
using MediaColor = System.Windows.Media.Color;

namespace CapsLockShow.Views;

public sealed class FlyoutWindow : Forms.Form
{
    private const int FlyoutWidth = 240;
    private const int FlyoutHeight = 72;
    private const int CornerRadius = 12;
    private const int IconSize = 34;
    private const int ContentLeft = 20;
    private const int ContentTop = 11;
    private const int IndicatorHeight = 4;
    private const int IndicatorBottom = 7;

    private readonly Forms.Timer _hideTimer = new();
    private readonly Forms.Timer _animationTimer = new() { Interval = 15 };
    private AppSettings _settings = new();
    private LockKey? _key;
    private bool _isOn;
    private Color _accent = Color.FromArgb(0, 120, 212);
    private DateTime _animationStarted;
    private TimeSpan _animationDuration;
    private Point _animationStartLocation;
    private Point _animationTargetLocation;
    private double _animationStartOpacity;
    private double _animationTargetOpacity;
    private Action? _animationCompleted;

    public FlyoutWindow()
    {
        AutoScaleMode = Forms.AutoScaleMode.None;
        BackColor = Color.Black;
        ClientSize = new Size(FlyoutWidth, FlyoutHeight);
        DoubleBuffered = true;
        FormBorderStyle = Forms.FormBorderStyle.None;
        MaximizeBox = false;
        MinimizeBox = false;
        ShowInTaskbar = false;
        StartPosition = Forms.FormStartPosition.Manual;
        TopMost = true;

        _hideTimer.Tick += (_, _) => HideAnimated();
        _animationTimer.Tick += (_, _) => AdvanceAnimation();
        SizeChanged += (_, _) => ApplyRoundedRegion();
        ApplyRoundedRegion();
    }

    protected override bool ShowWithoutActivation => true;

    protected override Forms.CreateParams CreateParams
    {
        get
        {
            var cp = base.CreateParams;
            cp.ExStyle |= NativeMethods.WS_EX_NOACTIVATE | NativeMethods.WS_EX_TOOLWINDOW;
            return cp;
        }
    }

    public void ApplySettings(AppSettings settings)
    {
        _settings = settings;
    }

    public void ShowState(LockKey key, bool isOn)
    {
        _hideTimer.Stop();
        _key = key;
        _isOn = isOn;
        _accent = ToDrawingColor(ThemeService.AccentColor());
        Invalidate();

        var target = TargetPosition();
        var offset = target.Y > 80 ? 20 : -20;
        var start = new Point(target.X, target.Y + offset);

        if (!Visible)
        {
            Location = start;
            Opacity = 0;
            Show();
            ApplyRoundedRegion();
        }

        BringTopmostWithoutFocus();
        AnimateTo(target, 1, 180, null);
        _hideTimer.Interval = Math.Max(1, _settings.DurationMs);
        _hideTimer.Start();
    }

    protected override void OnPaint(Forms.PaintEventArgs e)
    {
        base.OnPaint(e);

        var graphics = e.Graphics;
        graphics.SmoothingMode = SmoothingMode.AntiAlias;
        graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;

        var dark = ThemeService.IsDark(_settings.Theme);
        using var surfaceBrush = new SolidBrush(dark ? Color.FromArgb(32, 32, 32) : Color.FromArgb(252, 252, 252));
        using var borderPen = new Pen(dark ? Color.FromArgb(30, 255, 255, 255) : Color.FromArgb(24, 0, 0, 0), 1f);
        using var surfacePath = RoundedRect(new RectangleF(0.5f, 0.5f, ClientSize.Width - 1f, ClientSize.Height - 1f), CornerRadius);
        graphics.FillPath(surfaceBrush, surfacePath);
        graphics.DrawPath(borderPen, surfacePath);

        if (_key is null)
        {
            return;
        }

        DrawIcon(graphics, dark);
        DrawText(graphics, dark);
        DrawIndicator(graphics);
    }

    private void DrawIcon(Graphics graphics, bool dark)
    {
        var muted = dark ? Color.FromArgb(140, 255, 255, 255) : Color.FromArgb(125, 0, 0, 0);
        var border = _isOn ? _accent : muted;
        var fill = Blend(Color.Transparent, _accent, _isOn ? 0.11f : 0.055f, dark);
        var iconBounds = new RectangleF(ContentLeft, 17, IconSize, IconSize);

        using var iconPath = RoundedRect(iconBounds, 7);
        using var fillBrush = new SolidBrush(fill);
        using var borderPen = new Pen(border, 1.4f);
        graphics.FillPath(fillBrush, iconPath);
        graphics.DrawPath(borderPen, iconPath);

        using var symbolFont = new Font("Segoe UI Variable", _key?.Name == "Scroll Lock" ? 14f : 15f, FontStyle.Bold, GraphicsUnit.Point);
        using var symbolBrush = new SolidBrush(_isOn ? _accent : muted);
        using var format = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center };
        graphics.DrawString(_key?.Symbol ?? string.Empty, symbolFont, symbolBrush, iconBounds, format);
    }

    private void DrawText(Graphics graphics, bool dark)
    {
        if (_key is null)
        {
            return;
        }

        var textLeft = ContentLeft + IconSize + 14;
        var titleColor = dark ? Color.FromArgb(243, 243, 243) : Color.FromArgb(31, 31, 31);
        var muted = dark ? Color.FromArgb(140, 255, 255, 255) : Color.FromArgb(125, 0, 0, 0);

        using var titleFont = new Font("Microsoft YaHei UI", 9.5f, FontStyle.Bold, GraphicsUnit.Point);
        using var statusFont = new Font("Microsoft YaHei UI", 8.5f, FontStyle.Regular, GraphicsUnit.Point);
        using var titleBrush = new SolidBrush(titleColor);
        using var statusBrush = new SolidBrush(muted);

        graphics.DrawString(_key.Name, titleFont, titleBrush, new PointF(textLeft, ContentTop + 5));
        graphics.DrawString(_isOn ? "已开启" : "已关闭", statusFont, statusBrush, new PointF(textLeft, ContentTop + 25));
    }

    private void DrawIndicator(Graphics graphics)
    {
        var indicatorWidth = _isOn ? 96 : 52;
        var indicatorLeft = (ClientSize.Width - indicatorWidth) / 2f;
        var indicatorTop = ClientSize.Height - IndicatorBottom - IndicatorHeight;
        var indicatorColor = Color.FromArgb(_isOn ? 255 : 110, _accent);

        using var path = RoundedRect(new RectangleF(indicatorLeft, indicatorTop, indicatorWidth, IndicatorHeight), 2);
        using var brush = new SolidBrush(indicatorColor);
        graphics.FillPath(brush, path);
    }

    private void HideAnimated()
    {
        _hideTimer.Stop();
        if (!Visible)
        {
            return;
        }

        var offset = Top > 80 ? 20 : -20;
        AnimateTo(new Point(Left, Top + offset), 0, 160, Hide);
    }

    private void AnimateTo(Point target, double opacity, int durationMs, Action? completed)
    {
        _animationTimer.Stop();
        _animationStarted = DateTime.UtcNow;
        _animationDuration = TimeSpan.FromMilliseconds(durationMs);
        _animationStartLocation = Location;
        _animationTargetLocation = target;
        _animationStartOpacity = Opacity;
        _animationTargetOpacity = opacity;
        _animationCompleted = completed;
        _animationTimer.Start();
    }

    private void AdvanceAnimation()
    {
        var elapsed = DateTime.UtcNow - _animationStarted;
        var progress = _animationDuration.TotalMilliseconds <= 0
            ? 1
            : Math.Clamp(elapsed.TotalMilliseconds / _animationDuration.TotalMilliseconds, 0, 1);
        var eased = EaseOutCubic(progress);

        Left = Lerp(_animationStartLocation.X, _animationTargetLocation.X, eased);
        Top = Lerp(_animationStartLocation.Y, _animationTargetLocation.Y, eased);
        Opacity = Lerp(_animationStartOpacity, _animationTargetOpacity, eased);

        if (progress < 1)
        {
            return;
        }

        _animationTimer.Stop();
        var completed = _animationCompleted;
        _animationCompleted = null;
        completed?.Invoke();
    }

    private void ApplyRoundedRegion()
    {
        using var path = RoundedRect(new RectangleF(0, 0, ClientSize.Width, ClientSize.Height), CornerRadius);
        Region?.Dispose();
        Region = new Region(path);
    }

    private Point TargetPosition()
    {
        var cursor = Forms.Cursor.Position;
        var screen = Forms.Screen.FromPoint(cursor);
        var area = screen.WorkingArea;
        const int margin = 24;

        return _settings.Position switch
        {
            "bottom_left" => new Point(area.Left + margin, area.Bottom - Height - margin),
            "bottom_right" => new Point(area.Right - Width - margin, area.Bottom - Height - margin),
            "top_center" => new Point(area.Left + (area.Width - Width) / 2, area.Top + margin),
            _ => new Point(area.Left + (area.Width - Width) / 2, area.Bottom - Height - margin)
        };
    }

    private void BringTopmostWithoutFocus()
    {
        TopMost = false;
        TopMost = true;
    }

    private static GraphicsPath RoundedRect(RectangleF bounds, float radius)
    {
        var diameter = radius * 2;
        var path = new GraphicsPath();
        path.AddArc(bounds.Left, bounds.Top, diameter, diameter, 180, 90);
        path.AddArc(bounds.Right - diameter, bounds.Top, diameter, diameter, 270, 90);
        path.AddArc(bounds.Right - diameter, bounds.Bottom - diameter, diameter, diameter, 0, 90);
        path.AddArc(bounds.Left, bounds.Bottom - diameter, diameter, diameter, 90, 90);
        path.CloseFigure();
        return path;
    }

    private static Color ToDrawingColor(MediaColor color)
    {
        return Color.FromArgb(color.R, color.G, color.B);
    }

    private static Color Blend(Color background, Color foreground, float amount, bool dark)
    {
        if (background == Color.Transparent)
        {
            background = dark ? Color.FromArgb(32, 32, 32) : Color.FromArgb(252, 252, 252);
        }

        var inverse = 1 - amount;
        return Color.FromArgb(
            (int)(background.R * inverse + foreground.R * amount),
            (int)(background.G * inverse + foreground.G * amount),
            (int)(background.B * inverse + foreground.B * amount));
    }

    private static int Lerp(int start, int end, double amount)
    {
        return (int)Math.Round(start + (end - start) * amount);
    }

    private static double Lerp(double start, double end, double amount)
    {
        return start + (end - start) * amount;
    }

    private static double EaseOutCubic(double value)
    {
        return 1 - Math.Pow(1 - value, 3);
    }
}
