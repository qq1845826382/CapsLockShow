using System;
using System.Windows;
using System.Windows.Threading;
using CapsLockShow.Services;
using WpfApplication = System.Windows.Application;
using WpfMessageBox = System.Windows.MessageBox;

namespace CapsLockShow;

public partial class App : WpfApplication
{
    private AppController? _controller;

    protected override void OnStartup(StartupEventArgs e)
    {
        NativeMethods.SetCurrentProcessExplicitAppUserModelID(AppConstants.AppUserModelId);
        DispatcherUnhandledException += OnDispatcherUnhandledException;
        base.OnStartup(e);

        _controller = new AppController(this);
        _controller.Start();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _controller?.Dispose();
        base.OnExit(e);
    }

    private static void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        WpfMessageBox.Show(e.Exception.Message, AppConstants.AppName, MessageBoxButton.OK, MessageBoxImage.Error);
        e.Handled = true;
    }
}
