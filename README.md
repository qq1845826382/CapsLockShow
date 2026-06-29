# CapsLockShow

CapsLockShow 是一个面向 Windows 10/11 的锁定键浮窗工具，只显示 `Caps Lock`、`Num Lock` 和 `Scroll Lock` 的状态变化。

## Features

- 托盘常驻应用，提供设置、预览、自启动和退出菜单。
- 使用 Win32 `WH_KEYBOARD_LL` 全局低级键盘钩子，在 `WM_KEYUP` 后读取最终锁定键状态。
- 启动后显示一次当前 Caps Lock 状态，确认应用已运行。
- 浮窗显示在鼠标所在屏幕，支持底部居中、左下角、右下角和顶部居中。
- 可在 DirectX 独占全屏时隐藏浮窗。
- 设置保存到 `%APPDATA%\CapsLockShow\config.json`，兼容旧版字段。
- 可写入当前用户自启动项：`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`。

## Requirements

- Windows 10/11
- .NET 8 Desktop Runtime

## Development

```powershell
dotnet restore
dotnet run
```

## Build

```powershell
.\build.ps1
```

构建产物输出到 `dist\CapsLockShow.exe`。`dist` 不提交到仓库，发布文件通过 Release 分发。

## License

This project is licensed under GPLv3.
