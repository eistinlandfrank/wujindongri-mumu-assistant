# 无尽冬日 MuMu 助手 5.8.0

面向 MuMu Player 的 Windows 桌面助手。使用 MuMu 安装自带的渲染 IPC 读取游戏画面，用 ADB 绑定实例并执行已确认的操作。

## 下载和使用

1. 在 Windows 10 或 11 的 64 位系统上启动 MuMu Player，并为目标实例启用 ADB。
2. 从 [GitHub Releases](https://github.com/eistinlandfrank/wujindongri-mumu-assistant/releases) 获取 `WJDRMuMuAssistant_v5.8.0_Portable.exe`。双击即可启动，首次运行会校验并解压到本机用户目录。使用便携版无需安装 Python。
3. 在顶部选择手机。通过「多手机窗口」分别打开其他账号的窗口。任务、配置和日志按账号隔离。
4. 从左侧选择任务。顶部「停止当前」只停止当前窗口，**F8** 停止所有助手窗口中的任务并取消尚未开始的预约。左下角的太阳、月亮和「系统」分别切换全局浅色、深色和跟随 Windows。

## 功能

- **巨兽集结**。按账号设置等级、兵种数量、同时集结数和体力预算。只有识别到当前编组、目标和队列状态时才执行对应操作。
- **每日任务、联盟帮助和联盟红包**。按当前游戏页面确认可执行步骤。遇到未知界面时，按流程等待复核或停止输入。
- **堡垒跑联盟**。按站保存联盟和目标信息，支持定时启动。也可用[堡垒路线脚本](scripts/fortress_route.md)进行预演。
- **备战积分**。导入 Excel 或 CSV、读取榜单、保存快照并比较变动。比较依赖可唯一匹配的国家和昵称，保存前应核对识别结果。
- **定时启动与任务编排**。为已绑定账号安排单次启动，或编辑可复用操作。预约到点时，电脑、游戏和对应助手窗口须保持运行。

## 源码运行和构建

```powershell
python -m pip install -r requirements.txt
python src/wjdr_mumu_assistant_qt.py
```

在源码启动命令后加 `--device <ADB序列号>` 可指定在线实例。查找实现可参考[代码模块索引](docs/code-map.md)。识图命令见[快速识图工具](docs/fast-vision.md)。

编译便携版需要 PyInstaller 和 Windows .NET Framework 的 C# 编译器。在仓库目录执行以下命令。

```powershell
python -m pip install pyinstaller
.\packaging\build_release.ps1 -OutputRoot release
.\packaging\build_portable.ps1 -OutputRoot release -SkipRuntime
```

输出为 `release/WJDRMuMuAssistant_v5.8.0_Portable.exe`。封装时会校验运行目录中的代码与素材是否和当前源码一致。
