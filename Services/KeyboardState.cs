namespace CapsLockShow.Services;

public static class KeyboardState
{
    public static bool IsToggled(int virtualKey) => (NativeMethods.GetKeyState(virtualKey) & 0x0001) != 0;
}
