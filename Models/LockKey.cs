namespace CapsLockShow.Models;

public sealed record LockKey(int VirtualKey, string Name, string Symbol)
{
    public bool IsEnabled(AppSettings settings) => VirtualKey switch
    {
        NativeMethods.VK_CAPITAL => settings.CapsEnabled,
        NativeMethods.VK_NUMLOCK => settings.NumEnabled,
        NativeMethods.VK_SCROLL => settings.ScrollEnabled,
        _ => false
    };
}
