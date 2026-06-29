using System.Collections.Generic;
using System.Linq;
using CapsLockShow.Models;

namespace CapsLockShow.Services;

public static class LockKeys
{
    public static readonly LockKey CapsLock = new(NativeMethods.VK_CAPITAL, "Caps Lock", "A");
    public static readonly LockKey NumLock = new(NativeMethods.VK_NUMLOCK, "Num Lock", "1");
    public static readonly LockKey ScrollLock = new(NativeMethods.VK_SCROLL, "Scroll Lock", "↕");

    public static IReadOnlyList<LockKey> All { get; } = [CapsLock, NumLock, ScrollLock];

    public static LockKey? FromVirtualKey(int virtualKey) => All.FirstOrDefault(key => key.VirtualKey == virtualKey);

    public static LockKey? FromName(string name) => All.FirstOrDefault(key => key.Name == name);
}
