#!/bin/bash
# LiveCSV 非阻塞启动脚本 (Linux) / non-blocking launcher.
# 后台启动 Flask 服务，立即返回终端，不阻塞。
# Starts the Flask server in the background and returns the terminal at once.

cd "$(dirname "$0")" || exit 1

# ---- 检测是否已有实例在运行（匹配运行 livecsv.py 的进程）----
# ---- Check if an instance is already running (matches a process running livecsv.py) ----
if pgrep -f "livecsv\.py" >/dev/null 2>&1; then
    echo "LiveCSV 已在运行，跳过本次启动。"
    echo "LiveCSV is already running; skipping launch."
    exit 0
fi

# ---- 选择 python 解释器（Linux 上通常是 python3）----
# ---- Pick the python interpreter (usually python3 on Linux) ----
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[错误] 未找到 python，请先安装 Python 3。"
    echo "[error] python not found; please install Python 3 first."
    exit 1
fi

mkdir -p logs

echo "========================================"
echo "  启动 LiveCSV / Starting LiveCSV"
echo "========================================"
echo

# ---- 后台脱机启动 ----
# nohup  : 忽略 SIGHUP，终端关闭后进程不退出
# > log  : 重定向输出（避免 nohup.out，保留启动日志）
# &      : 放入后台，立即返回
# disown : 解除与当前 shell 的作业关联
# ---- Launch detached in the background ----
# nohup : ignore SIGHUP so the process survives terminal close
# > log : redirect output (avoids nohup.out, keeps a startup log)
# &     : run in background, return immediately
# disown: detach from this shell's job table
nohup "$PY" livecsv.py > logs/startup.log 2>&1 &
echo $! > livecsv.pid
disown

echo "正在启动 LiveCSV 服务..."
echo "Starting LiveCSV service..."
sleep 3

echo "LiveCSV 已在后台启动（PID: $(cat livecsv.pid)），浏览器将自动打开。"
echo "LiveCSV started in the background (PID: $(cat livecsv.pid)); the browser will open automatically."
echo "启动日志 / Startup log: logs/startup.log"
echo
echo "如需退出 / To quit: kill \"\$(cat livecsv.pid)\""
echo
