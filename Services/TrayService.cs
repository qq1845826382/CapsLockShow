using System;
using System.Drawing;
using System.Windows;
using Forms = System.Windows.Forms;
using WpfApplication = System.Windows.Application;

namespace CapsLockShow.Services;

public sealed class TrayService : IDisposable
{
    private readonly Forms.NotifyIcon _notifyIcon;
    private readonly Forms.ToolStripMenuItem _startupItem;

    public TrayService(Icon icon)
    {
        _notifyIcon = new Forms.NotifyIcon
        {
            Icon = icon,
            Text = AppConstants.AppName,
            Visible = true
        };

        var menu = new Forms.ContextMenuStrip();
        menu.Items.Add("打开设置", null, (_, _) => OpenSettingsRequested?.Invoke(this, EventArgs.Empty));

        var testMenu = new Forms.ToolStripMenuItem("测试浮窗");
        foreach (var key in LockKeys.All)
        {
            testMenu.DropDownItems.Add(key.Name, null, (_, _) => TestFlyoutRequested?.Invoke(this, key.Name));
        }
        menu.Items.Add(testMenu);

        menu.Items.Add(new Forms.ToolStripSeparator());
        _startupItem = new Forms.ToolStripMenuItem("开机自启动")
        {
            CheckOnClick = true
        };
        _startupItem.CheckedChanged += StartupItemOnCheckedChanged;
        menu.Items.Add(_startupItem);

        menu.Items.Add(new Forms.ToolStripSeparator());
        menu.Items.Add("退出", null, (_, _) => WpfApplication.Current.Shutdown());

        _notifyIcon.ContextMenuStrip = menu;
        _notifyIcon.DoubleClick += (_, _) => OpenSettingsRequested?.Invoke(this, EventArgs.Empty);
    }

    public event EventHandler? OpenSettingsRequested;
    public event EventHandler<string>? TestFlyoutRequested;
    public event EventHandler<bool>? StartupChanged;

    public void SyncStartup(bool enabled)
    {
        if (_startupItem.Checked == enabled)
        {
            return;
        }

        _startupItem.CheckedChanged -= StartupItemOnCheckedChanged;
        _startupItem.Checked = enabled;
        _startupItem.CheckedChanged += StartupItemOnCheckedChanged;
    }

    public void Dispose()
    {
        _notifyIcon.Visible = false;
        _notifyIcon.Dispose();
    }

    private void StartupItemOnCheckedChanged(object? sender, EventArgs e)
    {
        StartupChanged?.Invoke(this, _startupItem.Checked);
    }
}
