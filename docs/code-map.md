# 代码模块索引

开发时先按职责打开对应模块，避免默认读取整个桌面程序。

| 任务 | 首选文件 |
| --- | --- |
| 程序入口、设备选择、工作线程、野兽和红包流程 | `wjdr_mumu_assistant_qt.py` |
| 每日 325 的扫描、采集、训练、情报等流程 | `wjdr_daily_controller.py` |
| 主窗口页面的创建、布局和样式 | `wjdr_frontend_layout.py` |
| 截图控件、设置对话框和界面信号 | `wjdr_ui_components.py` |
| 桌面工作流共用的超时和重试常量 | `wjdr_runtime_config.py` |
| ADB、设备身份、持久化和底层图像识别 | `wjdr_backend.py` |
| 野兽状态和账本语义 | `wjdr_beast_hunt.py`、`wjdr_beast_supervision.py` |
| 每日情报、探险及视觉辅助 | `wjdr_daily_intel.py`、`wjdr_daily_expedition.py`、`wjdr_daily_visuals.py` |
| 定时计划、战备积分 | `wjdr_schedule*.py`、`wjdr_scoreboard*.py` |

`MainWindow._start_daily_rewards_flow` 是兼容入口，实际实现位于
`wjdr_daily_controller.DailyController._start_daily_rewards_flow`；界面方法通过
`FrontendLayout` 混入。查找每日子流程可直接搜索 `run_gather_plan`、
`run_intel_rescue_plan`、`run_shield_training_plan`、
`run_alliance_food_donation_plan` 等名称。

每日控制器当前仍是一个闭包，多个子流程共享运行时状态；它已经与窗口入口隔离，
但还没有拆成独立的可复用状态对象。后续拆分这些子流程应先明确状态所有权和
设备绑定，保留既有输入确认和持久化检查，并分别验证受影响的真实设备路径。

新增本地模块时，应确认 PyInstaller 能解析入口的静态导入，并同步
`scripts/verify_frozen_source.py` 的核验清单；如果使用本机的增量构建脚本，
也要同步其模块清单。源码能导入并不等于便携包已包含最新代码。
