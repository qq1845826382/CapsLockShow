namespace CapsLockShow.Services;

public static class FullscreenService
{
    public static bool IsDirectxFullscreen()
    {
        return NativeMethods.SHQueryUserNotificationState(out var state) == 0
               && state == NativeMethods.QUNS_RUNNING_D3D_FULL_SCREEN;
    }
}
