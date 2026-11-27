# 堡垒跑联盟脚本

复制 `scripts/fortress_route.example.json` 后填写本轮数据。`stops` 从上往下执行，同一盟的堡垒和要塞写在同一个 `targets` 里。

| 字段 | 填法 |
| --- | --- |
| `device` 和 `mumu_index` | 实际选定的 ADB 序列号与 MuMu 编号。当前 2 号示例为 `127.0.0.1:16448` 和 `2`。 |
| `round_start` | 本轮邮件的时间起点，按北京时间填到秒。 |
| `start_at` | 可选。首站预约启动时间，按北京时间填到秒。 |
| `take_keys` | `false` 跑完胜利邮件就结束。`true` 计算每个联盟的钥匙返回截止并开放返回流程。 |
| `capture` | `ipc`，可省略。脚本使用 MuMu IPC 截图。 |
| `alliance` | 游戏方括号里的短标签，例如 `ABC`。 |
| `targets` | 同一站可填写多个目标。堡垒编号为 1–12，要塞编号为 1–4，每个目标的 `mode` 可分别选 `单撞` 或 `集结`。选全部报名时填写 `[{"kind":"全部报名"}]`，也可加一个整站打法。省略普通堡垒的 `number` 对应旧路线的唯一堡垒模式。 |

从项目目录运行预演。预演只读配置。

```powershell
python scripts/run_fortress_route.py scripts/fortress_route.example.json
```

## 下一波自动跑盟

复制示例配置，填写本轮联盟短标签、目标编号和顺序。15:00 开跑可把 `round_start` 和 `start_at` 都设为 `2026-11-20 15:00:00`，按需要设置 `take_keys`。

```powershell
python scripts/run_fortress_route.py .\my-route.json --step auto-route --execute --wait-start --rapid-rate 100
```

到点后依次入盟。先在堡垒争夺页核对报名数量和目标编号，再从联盟主页进入「联盟战争」。识别已出军的堡垒或要塞，按照到达时间减 15 秒安排打开联盟邮件。相邻行军的等信区间重叠时留在邮件页，逐封领取。预计时间过后仍缺邮件时复核占领、邮件和后续出军。只有本站应领胜利邮件数核对完成，才立即开始去下一站。

集结看「集结」，单撞看「单人」，未填写打法时每 2 秒切换两个页签。两帧倒计时用于估算到达时间以及 30 分钟后的钥匙时间。收到胜利邮件后，以详情右上角的实际发件时间加 30 分钟分别安排返回。能够确认行军和钥匙结算相差不足 20 秒时，只跳过对应钥匙。返回后在联盟邮件中逐封核对「成功控制堡垒」的目标、实际发件时间和领取状态。出兵由玩家操作。

已核对目标数量和对应倒计时时，停留在联盟战争查看，预计到达前 15 秒切到邮件。便携版内置 PP-OCRv6 Tiny，用于识别标题、倒计时和邮件时间等局部区域。固定界面词可以容许一个字符的识别偏差，联盟短标签、编号和时间按原值核对。

领完本站胜利奖励后按原顺序前往下一站。钥匙保留各联盟的 30 分钟结算时间。路线完成后，按仍可赶上的返回截止时间排序处理钥匙。回盟后停留在联盟邮件页，发现本轮匹配的「成功控制堡垒」邮件即领取并登记。

堡垒跑盟的操作回执以 5 秒为纠错门槛。领取钥匙超时后，重新核对同一封邮件的礼物图标和详情领取状态，确认仍可领取才补点一次。复核后仍无法确认页面或回执时，停止该账号并显示卡点。

桌面端选择联盟行后点「选择目标」，也可双击「目标和打法」单元格。可以同时勾选多个堡垒和要塞，为每个目标选择打法。新站默认选「全部报名」，核对活动页的报名数量及每张卡片，并等待所有目标变为本联盟的蓝色占领。

在「堡垒跑联盟」页选择日期并调整时、分、秒后保存路线。未来的开始时间可点击「预约开跑」，并在「定时启动」页查看或取消。已到开始时间可点击「开始跑盟」。自动连点最多五分钟，超时会在状态栏和运行日志登记。若有待领取的钥匙，入盟超时后先回盟拿钥匙。为钥匙换盟时，只在返回截止前最后 20 秒内确认退盟。分批领取胜利奖励时，钥匙截止临近会核对一次下一波行军，再按间隔决定是否换盟。页面的「继续连点」可手动调整时长及速度。

「历史记录」按账号显示每轮路线、各站领取的胜利邮件及钥匙。保存新一轮时会归档已开始的旧一轮。历史每页显示 100 轮，可以翻页查看更早记录。

```powershell
python scripts/run_fortress_route.py .\my-route.json --step rapid-enter --execute --rapid-rate 100 --rapid-minutes 15
python scripts/run_fortress_route.py .\my-route.json --step rapid-enter --execute --rapid-rate 100 --rapid-unlimited
```

实际运行时换成自己的配置。每次用 `--step` 指定一个检查点，再加 `--execute`。

```powershell
python scripts/run_fortress_route.py .\my-route.json --step capture-check --execute
python scripts/run_fortress_route.py .\my-route.json --step enter --execute
```

从主城、野外或联盟主页开始 `enter`。若需要退出当前联盟，显式追加 `--leave-current`。需要审核时，脚本提交一次并等待入盟，三分钟未确认则在终端输出状态。用 `status` 查看同账号本轮的保存进度。

已在无盟页搜出本站并看到绿色「加入」时，可用 `rapid-enter-check` 做只读节拍检查。`rapid-enter` 在确认目标后按设定频率点击，后台单独检查页面。默认五分钟停止，可通过 `--rapid-minutes` 调整。若游戏结果仍待核对，脚本保留入盟记录并在终端报告。

连点默认每秒 10 次。可加 `--rapid-rate 100` 选择 MuMu IPC 触控，目标间隔 10 毫秒。配合 `rapid-enter-check` 时只测 IPC 往返和节拍。实际游戏输入需要 `rapid-enter`。

填了 `start_at` 的路线可预约首站。预约要求电脑与脚本保持运行，按 `Ctrl+C` 可以取消等待。超过预约时间 30 秒或同一轮已有预约启动记录时，脚本会停止。后续站按占领和邮件进度推进。

```powershell
python scripts/run_fortress_route.py .\my-route.json --step enter --execute --wait-start --leave-current
```

按配置中的单撞或集结组织进攻。若执行单撞，在发兵前用 `solo-ready` 核对间隔，发兵后用 `solo-record` 登记。实际发兵目前仍由玩家操作。

等目标占领后执行 `occupation`，然后用 `mail-list` 打开联盟邮件。逐封核对邮件确实属于本站和本轮，打开详情后传入右上角的发件时间。

也可以用 `--step auto-reward --execute` 串联占领核验、返回、打开联盟邮件和领取。它一次处理一封胜利邮件，要求本站入盟已确认。详情右上角发件时间需在本站入盟后，脚本会保留未确认的领取记录供续查。

```powershell
python scripts/run_fortress_route.py .\my-route.json --step reward --sent-at "2026-11-20 12:08:31" --execute
```

核对本站的胜利邮件全部登记后执行 `advance`。`take_keys` 为 `true` 时，`status` 会按各盟最早一封胜利邮件加 30 分钟的截止时间列出待返回联盟。`return-keys` 进入最早到期且仍可按时返回的一站。结算后可运行 `key-mail` 在当前联盟邮件核对并领取，手动领取可用 `key-record` 登记。

IPC 帧绑定到选定实例和游戏显示。截图异常时当前步骤停止，已写入的领邮件或申请记录会保留。
