using System;
using System.Runtime.InteropServices;
using System.Threading;

namespace CapsLockShow.Services;

public sealed class KeyboardHookService : IDisposable
{
    private readonly NativeMethods.LowLevelKeyboardProc _hookProc;
    private readonly Thread _thread;
    private IntPtr _hookId;
    private uint _threadId;
    private bool _disposed;

    public KeyboardHookService()
    {
        _hookProc = HandleKeyboardEvent;
        _thread = new Thread(MessageLoop)
        {
            IsBackground = true,
            Name = "CapsLockShow keyboard hook"
        };
    }

    public event EventHandler<int>? KeyReleased;

    public void Start()
    {
        _thread.Start();
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;

        if (_threadId != 0)
        {
            NativeMethods.PostThreadMessage(_threadId, NativeMethods.WM_QUIT, UIntPtr.Zero, IntPtr.Zero);
        }

        if (_thread.IsAlive && !_thread.Join(TimeSpan.FromSeconds(1)))
        {
            // The hook thread is background; process exit will tear it down if Windows is slow to release it.
        }
    }

    private void MessageLoop()
    {
        _threadId = NativeMethods.GetCurrentThreadId();
        var module = NativeMethods.GetModuleHandle(null);
        _hookId = NativeMethods.SetWindowsHookEx(NativeMethods.WH_KEYBOARD_LL, _hookProc, module, 0);

        if (_hookId == IntPtr.Zero)
        {
            return;
        }

        try
        {
            while (NativeMethods.GetMessage(out var message, IntPtr.Zero, 0, 0) != 0)
            {
                NativeMethods.TranslateMessage(ref message);
                NativeMethods.DispatchMessage(ref message);
            }
        }
        finally
        {
            NativeMethods.UnhookWindowsHookEx(_hookId);
            _hookId = IntPtr.Zero;
        }
    }

    private IntPtr HandleKeyboardEvent(int nCode, IntPtr wParam, IntPtr lParam)
    {
        if (nCode == NativeMethods.HC_ACTION
            && (wParam.ToInt32() == NativeMethods.WM_KEYUP || wParam.ToInt32() == NativeMethods.WM_SYSKEYUP))
        {
            var hookStruct = Marshal.PtrToStructure<NativeMethods.KbdLlHookStruct>(lParam);
            var virtualKey = (int)hookStruct.VkCode;

            if (LockKeys.FromVirtualKey(virtualKey) is not null)
            {
                KeyReleased?.Invoke(this, virtualKey);
            }
        }

        return NativeMethods.CallNextHookEx(_hookId, nCode, wParam, lParam);
    }
}
