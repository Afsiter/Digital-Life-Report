# 📟 Digital Life Report
**你的数字人生年度报告生成器**  

![alt text](https://img.shields.io/badge/platform-Windows-0078D6.svg)
![alt text](https://img.shields.io/badge/python-3.8+-yellow.svg)

## 📖 简介 (Introduction)

Digital Life Report 是一个轻量级的 Python 工具，它通过扫描 Windows 系统底层的事件日志（System & Application Logs），挖掘你过去一年的电脑使用习惯。

### ✨ 效果预览 (Preview)
![preview.png](./figure/preview.png)

### ✨ 主要功能 (Features)

#### 🏆 成就系统
根据你的使用习惯解锁“赛博铁人”、“暗夜伯爵”、“蓝屏受害者”等成就。

#### 📊 视觉化图表

24小时活跃度：你是晨型人还是夜猫子？

摸鱼 vs 搬砖：工作日与周末的活跃对比。

周常规律：一周中哪天你最离不开电脑。

#### 💀 稳定性分析
统计蓝屏（BSOD）和异常断电次数，并在崩溃数据下附带“暖心”吐槽。

#### 🤖 铁人记录
计算你单次最长连续开机时间。

### 🔒 隐私安全
所有数据处理完全在本地运行，不上传任何服务器。

## 🛠️ 环境要求

操作系统: `Windows 10 / Windows 11` (依赖 `PowerShell` `Get-WinEvent` 指令)

Python: `Python 3.6+` (如果直接运行源码)

权限: **管理员权限 (Administrator)** (推荐，否则可能无法读取完整的系统日志)

## 🚀 使用指南 (Usage)

### 方式一：直接运行 exe 文件
仓库中已提供打包好的exe文件`digital_life.exe`，若不信任该文件可根据python脚本自行打包。

### 方式二：直接运行 python 脚本

克隆或下载本项目，确保 `digital_life.py` 在你的文件夹中。

**以管理员身份打开终端**（`CMD` 或 `PowerShell`）。（普通用户权限可能只能读取部分数据）

运行脚本：
```
python digital_life.py
```

输入你想查询的年份（例如 2025），按回车。

脚本将在当前目录生成 `my_digital_life_2025.html` 并自动在浏览器中打开。


## 🔍 原理解析 (How it works)

脚本底层调用 Windows PowerShell 执行以下查询：

Event ID 6005: EventLog 服务启动（视为开机）

Event ID 6006: EventLog 服务停止（视为关机）

Event ID 41: Kernel-Power（异常关机/断电）

Event ID 1001: BugCheck（蓝屏死机）

Event ID 1033: MsiInstaller（软件安装）

通过 Python 对这些时间戳进行清洗、配对和统计，最终嵌入 ECharts 生成可视化 HTML。

## ⚠️ 免责声明 (Disclaimer)

请在使用前仔细阅读以下条款：

* 软件性质：本软件仅供个人娱乐和统计使用。作者不对软件生成的统计数据的绝对准确性负责。

* 数据安全：本软件纯本地运行，不会将任何数据上传至互联网。生成的 HTML 报告包含您的作息规律信息，请勿随意分享给不可信的第三方。

* 杀毒软件误报：由于本软件在后台调用 PowerShell 读取系统日志，某些杀毒软件（如 360、Windows Defender）可能会将其识别为“可疑行为”或“Trojan/Malware”。这是读取系统底层的正常特征，属于误报。如果您不信任，请直接审查并运行 Python 源码。

* 禁止用于违法用途：使用时请遵守相关法律法规，严禁将本软件用于未经授权的员工监控、他人隐私窥探等违法用途。在公司或公共电脑上运行前，请务必遵守相关 IT 政策。

* 责任限制：本软件按“原样”提供，作者不承担因使用本软件导致的任何直接或间接损失（包括但不限于系统崩溃、数据丢失）。

## 🤝 致谢 (Acknowledgments)
* AI Co-pilot: 本项目的核心逻辑优化与 UI 设计由 Google Gemini 辅助完成。
