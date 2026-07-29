# 无尽冬日 MuMu 助手 4.1.1

一个面向 MuMu Player 12 的 Windows 桌面工具。它通过 ADB 截图和模拟点击执行页面识别与联盟互助流程，不读取游戏内存、不修改 APK，也不读取账号密码。

## 主要能力

- 自动识别主城、联盟主页和联盟互助页面。
- 按“主城 / 世界地图 → 联盟 → 联盟互助 → 全部帮助”完成导航；只有确认联盟互助标题与绿色“全部帮助”按钮后才点击。
- 点击后重新截图确认；按钮消失时会丢弃旧坐标，避免持续盲点。
- 自动抢红包采用“红包浮标 → 聊天 → 联盟频道 → 熔炉升级红包 → 开启 → 结果页”逐步视觉确认；没有连续页面证据时不点击。
- 支持 MuMu 多开：每个窗口固定绑定一个独立 ADB 设备，并防止同一实例被重复执行。
- 高 DPI 界面与跨分辨率模板缩放识别。

## 本地运行

需要 Windows 10/11、MuMu Player 12，以及已启用 ADB 的游戏实例。

```powershell
py -m pip install -r requirements.txt
py wjdr_mumu_assistant_qt.py
```

程序默认会扫描 MuMu 实例；也可通过界面选择目标实例。运行中的自动任务可用 `F8` 紧急停止。

要生成便携版，请在 PowerShell 中运行：

```powershell
.\build_release.ps1
```

生成的便携版目录为 `release\\dist\\WJDRMuMuAssistant`。

## 项目文件

- `wjdr_mumu_assistant_qt.py`：当前 PySide6 桌面界面与任务编排。
- `wjdr_backend.py`：ADB、实例识别、截图匹配与点击逻辑。
- `alliance_*_builtin.png`：页面流程识别所需的内置模板。
- `assets/`：红包流程的内置识别模板。
- `installer.iss`、`version_info.txt`：Windows 打包配置。

## 注意

游戏服务条款可能禁止自动化、宏或机器人。请仅在自己承担风险的前提下进行短时、有人监看的测试，不要用于战斗、交易、充值或批量账号操作。
