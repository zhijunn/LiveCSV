# LiveCSV · 本地 CSV 实时查看器 | Local CSV Live Viewer

<p><img src="static/icon.png" width="72" height="72" alt="LiveCSV" /></p>

> 一个运行在本机和浏览器里的轻量 CSV / TSV 查看器：自适应表格、按列筛选、全文检索、多标签页、实时跟随文件更新。离线可用。
>
> A lightweight, local-first CSV/TSV viewer that runs on your machine and in your browser: adaptive
> table, per-column filters, full-text search, multi-tab, and live
> reload when the file changes. Works offline.

[简体中文](#中文) ｜ [English](#english)

---

## 中文

### 功能特性
- **自适应表格**：行高与列宽随内容自适应，点击单元格可展开超长内容；不同列以浅色背景区分，表头颜色略深。
- **按列筛选 + 全文检索**：每列独立筛选框加顶部全文检索，筛选、列宽、排序状态按窗口持久化，刷新或重启自动恢复。
- **实时更新**：本地文件被外部程序修改后，页面约 2 秒内自动刷新，保持筛选、排序、隐藏列与滚动位置不变。
- **多标签页**：同一窗口可打开多个文件，标签统一管理；每个标签独立保留筛选与滚动位置，后台文件变化切回时自动刷新；支持右键菜单与 Ctrl+~ 切换标签。
- **不锁文件**：以共享只读方式读取并立即释放，Office 等程序可同时读写，互不阻塞。
- **列布局**：默认显示全部列，可隐藏任意列；拖动表头右边缘调宽、拖动表头本体换位，序号 `#` 列固定；「自适应列宽」按钮一键按内容重排并清除已保存列宽。
- **记住状态**：刷新页面或关闭重开浏览器都会自动回到上次查看的文件；历史中可一键重开。
- **便捷功能**：用系统默认程序打开文件、在文件夹中定位、或在新窗口打开另一个文件，每个窗口独立记忆。
- **跨平台**：核心功能在 Windows / macOS / Linux 均可用；Windows 额外提供系统托盘与原生文件对话框，其他平台回退到 tkinter 且无托盘。
- **界面语言**：支持简体中文与英文，可在顶栏随时切换。
- **Windows 系统托盘**：启动后在任务栏托盘生成图标，菜单含「打开 WebUI」「退出」。
- **开箱即用**：前后端无需编译，安装 Python 依赖后即可运行。

### 使用方式

> 需要 Python 3.8+。

#### Python脚本启动

```bash
# 1) 克隆本仓库到本地
git clone https://github.com/zhijunn/LiveCSV.git
cd LiveCSV

# 2) 安装依赖
pip install -r requirements.txt

# 3) 启动（自动选取本地端口并打开浏览器）
python livecsv.py

# 可选参数
python livecsv.py --port 8080 --no-browser   # 指定端口、不自动打开浏览器
python livecsv.py --log-level INFO           # 日志等级，默认 WARNING（INFO 输出启动与请求日志）
```
启动后控制台会打印本地地址，如 `http://127.0.0.1:53170/`；在“选择文件”界面选择 CSV/TSV/TXT 文件，或从历史/示例中打开即可。

#### 一键后台启动

无需保留命令行窗口，运行后即在后台启动并自动打开浏览器：

| 系统 | 脚本 | 说明 |
| --- | --- | --- |
| Windows | 双击 `start_livecsv.bat` | 经 VBS 静默启动，无控制台黑窗常驻前台；服务在后台运行，启动窗口数秒后自动关闭；检测到已在运行时自动跳过，不重复启动。退出请点击系统托盘的 LiveCSV 图标 → 「退出」。 |
| Linux | `./start_livecsv.sh` | 用 `nohup` 脱机后台启动并立即返回终端；进程号写入 `livecsv.pid`，启动日志见 `logs/startup.log`；检测到已在运行时自动跳过。退出：`kill "$(cat livecsv.pid)"`。 |

> 提示：应用仅监听本地环回地址 `127.0.0.1`，不会暴露到外网。前端使用的 Vue 已下载到 `static/` 目录，**断网也能正常运行**。

### 使用场景
- 快速查看数据库导出、日志、报表等大型数据表。
- 在 Excel 打开同一文件的同时，用一个不锁文件的只读视图做对照查看。
- 监控采集器、定时任务持续写入的 CSV，页面自动跟随更新。

### 项目结构
```
livecsv.py              启动入口：解析参数、选端口、配置日志、启动服务
backend/                后端 Python 模块
  server.py             Flask 应用与 HTTP 接口
  csvio.py              CSV 读取：非锁式打开、编码探测、解析与缓存
  store.py              持久化状态：打开历史
  nativeops.py          系统集成：原生选择框、默认程序打开、文件夹定位
  tray.py               Windows 系统托盘图标
  log.py                服务端日志：按月归档
  make_icon.py          生成应用静态图标
frontend/               前端：浏览器端 Vue 3 应用
  index.html            页面骨架 + 内联 Vue 3 应用
  style.css             界面样式
  helpers.js            布局常量、API 端点表与纯函数工具
  messages.js           界面文案（中 / 英）
static/                 本地化前端资源：Vue 3 + 应用图标，支持断网运行
samples/                示例 CSV，便于体验功能
start_livecsv.bat/.sh   一键后台启动脚本（Windows / Linux）
requirements.txt        Python 依赖
LICENSE / README.md     MIT 许可证 / 项目说明

运行时生成文件已加入 .gitignore：state.json、uploads/、logs/、__pycache__/
```

### 开源协作原则
- 欢迎提 Issue 与 PR；请保持现有模块风格，小而专注、接口清晰。
- 修改涉及用户可见行为时，请在 PR 中说明动机与测试方式。
- 请勿提交 `state.json` 等个人本地状态或密钥、凭证等敏感信息，相关内容已在 `.gitignore` 中排除。
- 尊重现有许可证：本项目使用 MIT 协议开源，依赖见下。

---

## English

### Features
- **Adaptive table**: row height and column width adapt to content; click a cell to expand long values. Columns use light tints with slightly stronger headers.
- **Per-column filters + full-text search**: each column has its own filter box plus a global search; filter, width, and sort state is saved per window and restored on reload or restart.
- **Live updates**: when the local file is edited by another program, the view refreshes within ~2s, preserving filters, sort, hidden columns, and scroll position.
- **Multi-tab**: open several files at once and manage them in tabs; each tab keeps its own filters and scroll position and refreshes on switch when its file changed; right-click menu and Ctrl+~ to cycle tabs.
- **Non-locking reads**: files are opened read-only and released immediately, so Office and other tools can read/write them concurrently.
- **Column layout**: all columns show by default and any can be hidden; drag a header's right edge to resize or the header itself to reorder, with the `#` column fixed; an "Auto-fit widths" button resets to content-based widths and clears saved widths.
- **Remembers state**: refresh or close and reopen the browser and it returns to the last file; previously opened files reopen from history in one click.
- **Conveniences**: open with the default app, reveal in folder, or open another file in a new window — each window remembers its own state.
- **Cross-platform**: core features work on Windows / macOS / Linux. Windows adds a tray icon and native file dialog; other platforms fall back to a tkinter dialog with no tray icon.
- **UI languages**: Simplified Chinese and English, switchable anytime from the toolbar.
- **Windows tray icon**: a tray icon appears at startup with an "Open WebUI" / "Quit" menu.
- **Zero build**: no front-end or back-end compilation — install the Python dependencies and run.

### Quick Start
> Requires Python 3.8+.

#### Run with Python

```bash
git clone https://github.com/zhijunn/LiveCSV.git
cd LiveCSV
pip install -r requirements.txt
python livecsv.py
# python livecsv.py --port 8080 --no-browser
# python livecsv.py --log-level INFO        # default WARNING; INFO logs startup & requests
```
The console prints the local URL, e.g. `http://127.0.0.1:53170/`. On the
selection screen pick a CSV/TSV/TXT file, or open one from history/samples.

#### One-click background launch

Start the server in the background and open the browser automatically, with no terminal window left open:

| OS | Script | Notes |
| --- | --- | --- |
| Windows | double-click `start_livecsv.bat` | Starts silently via VBS (no console window); the server runs in the background and the launcher window auto-closes after a few seconds; skips launch if an instance is already running. Quit via the LiveCSV tray icon → "Quit". |
| Linux | `./start_livecsv.sh` | Launches detached with `nohup` and returns the terminal at once; the PID is written to `livecsv.pid` and startup output to `logs/startup.log`; skips launch if an instance is already running. Quit with `kill "$(cat livecsv.pid)"`. |

> The app listens only on the local loopback address `127.0.0.1` and is never exposed. Vue is bundled locally
> under `static/`, so it runs **fully offline**.

### Use Cases
- Inspect large exported tables like DB dumps, logs, and reports.
- Keep a non-locking read-only view side-by-side while Excel has the file open.
- Watch a CSV written continuously by collectors or scheduled jobs and let the
  page follow updates automatically.

### Project Structure
```
livecsv.py              launcher: parses CLI args, picks a port, configures logging, runs the server
backend/                backend Python modules
  server.py             Flask app & HTTP API
  csvio.py              CSV reading: non-locking open, encoding sniff, parse & cache
  store.py              persistent state: open history
  nativeops.py          OS integration: native file dialog, open-default, reveal
  tray.py               Windows system-tray icon
  log.py                server logging: monthly-rotating
  make_icon.py          generates the static app icons
frontend/               frontend: in-browser Vue 3 app
  index.html            page shell + inlined Vue 3 app
  style.css             UI styles
  helpers.js            layout constants, API endpoint map & pure helpers (display width, binary search, numeric check, JSON fetch wrappers)
  messages.js           UI strings (zh / en)
static/                 localized frontend assets: Vue 3 + app icon, runs offline
samples/                sample CSV files to try the features
start_livecsv.bat/.sh   one-click background launchers (Windows / Linux)
requirements.txt        Python dependencies
LICENSE / README.md     MIT license / project README

Generated at runtime (gitignored): state.json, uploads/, logs/, __pycache__/
```

### Collaboration Principles
- Issues and PRs welcome; please match the existing module style — small, focused
  modules with clear boundaries.
- For behavior-changing PRs, describe the motivation and how you tested it.
- Do not commit local user state like `state.json` or any secrets/credentials;
  these are already excluded via `.gitignore`.
- Respect existing licenses: this project is open-sourced under the MIT license, dependencies listed below.

---

### 第三方资源与许可 · Third-party & Licenses
| 资源 Resource | 用途 Purpose | 许可 License |
| --- | --- | --- |
| [Vue 3](https://vuejs.org/) (bundled in `static/`) | 前端框架 / frontend framework | MIT |
| [Flask](https://flask.palletsprojects.com/) | 后端 Web 框架 / backend framework | BSD-3-Clause |
| [pywin32](https://github.com/mhammond/pywin32) (Windows, optional) | 原生文件对话框 / native file dialog | PSF (Python Software Foundation License) |

## License
MIT — see [LICENSE](LICENSE).
