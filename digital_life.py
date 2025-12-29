import subprocess
import json
import datetime
import webbrowser
import os

# ================= 配置区 =================
# 默认年份，稍后会根据用户输入更新
YEAR = datetime.datetime.now().year 
HTML_FILE = f"./my_digital_life_{YEAR}.html"
# ========================================

def run_ps_command(cmd):
    """
    PowerShell 执行器：
    先获取二进制数据，再尝试 GBK (中文系统常见) 和 UTF-8 解码，
    防止因编码问题导致的崩溃。
    """
    try:
        # capture_output=True 会捕获 stdout 和 stderr，默认返回 bytes
        result = subprocess.run(["powershell", "-Command", cmd], capture_output=True)
        raw_bytes = result.stdout
        
        # 1. 尝试 GBK 解码
        try:
            return raw_bytes.decode('gbk')
        except UnicodeDecodeError:
            pass
            
        # 2. 尝试 UTF-8 解码
        try:
            return raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            pass
            
        # 3. 实在不行，忽略错误强制解码
        return raw_bytes.decode('utf-8', errors='ignore')
        
    except Exception as e:
        print(f"⚠️ PowerShell 执行底层错误: {e}")
        return ""

def get_hybrid_data(year):
    print(f"🕵️‍♂️ 正在扫描 {year} 年的数字足迹...")
    print("   [1/3] 正在分析系统启动与休眠日志...")
    print("   [2/3] 正在计算运行持续时间与稳定性...")
    print("   [3/3] 正在统计软件安装记录 (这可能需要几秒钟)...")
    
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # PowerShell 脚本：同时获取 System 和 Application 日志
    ps_script = f"""
    $s = Get-Date -Date "{start_date}"
    $e = Get-Date -Date "{end_date}"
    
    # 系统日志
    $sys = Get-WinEvent -FilterHashtable @{{LogName='System'; Id=6005,6006,41,1001,1,42; StartTime=$s; EndTime=$e}} -ErrorAction SilentlyContinue | 
           Select-Object Id, TimeCreated, @{{Name='Type';Expression={{'Sys'}}}}

    # 软件安装日志
    $apps = Get-WinEvent -FilterHashtable @{{LogName='Application'; ProviderName='MsiInstaller'; Id=1033; StartTime=$s; EndTime=$e}} -ErrorAction SilentlyContinue | 
            Select-Object Id, TimeCreated, @{{Name='Type';Expression={{'App'}}}}

    # 合并并按时间排序 (这对计算持续时间很重要)
    $all = $sys + $apps | Sort-Object TimeCreated
    $all | ConvertTo-Json -Depth 1
    """
    
    raw_json = run_ps_command(ps_script)
    
    if not raw_json.strip():
        return []

    try:
        data = json.loads(raw_json)
        if isinstance(data, dict): data = [data]
        return data if data else []
    except:
        return []

def parse_time(t_str):
    try:
        if "/Date(" in t_str:
            return datetime.datetime.fromtimestamp(int(t_str[6:-2])/1000)
        return datetime.datetime.fromisoformat(t_str.replace('Z', '+00:00'))
    except:
        return None

def analyze_hybrid(events):
    stats = {
        'boot': 0, 'shutdown': 0, 'crash': 0, 'bsod': 0, 'wake': 0, 'sleep': 0,
        'install_count': 0,
        'hour_dist': [0]*24, 
        'weekday_dist': [0]*7,
        'weekend_activity': 0,
        'weekday_activity': 0,
        'first_boot': None,
        'latest_session': None,
        'total_uptime_seconds': 0,
        'longest_session': {'duration': 0, 'date': None},
        'session_durations': []
    }
    
    last_boot_time = None
    
    for e in events:
        try:
            eid = e.get('Id')
            etype = e.get('Type')
            dt = parse_time(e.get('TimeCreated'))
            if not dt: continue
            
            if stats['first_boot'] is None: stats['first_boot'] = dt
            
            # --- 软件安装 ---
            if etype == 'App':
                stats['install_count'] += 1
                stats['hour_dist'][dt.hour] += 1
                continue

            # --- 系统事件 ---
            if eid == 6005: # 开机
                stats['boot'] += 1
                last_boot_time = dt 
                stats['hour_dist'][dt.hour] += 1
                stats['weekday_dist'][dt.weekday()] += 1
                if dt.weekday() >= 5: stats['weekend_activity'] += 1
                else: stats['weekday_activity'] += 1

            elif eid == 6006: # 关机
                stats['shutdown'] += 1
                if last_boot_time:
                    duration = (dt - last_boot_time).total_seconds()
                    if 0 < duration < 30 * 24 * 3600:
                        stats['total_uptime_seconds'] += duration
                        stats['session_durations'].append(duration)
                        if duration > stats['longest_session']['duration']:
                            stats['longest_session']['duration'] = duration
                            stats['longest_session']['date'] = last_boot_time
                    last_boot_time = None 

                if 0 <= dt.hour < 5:
                    if stats['latest_session'] is None or dt.time() > stats['latest_session'].time():
                         stats['latest_session'] = dt

            elif eid == 41: # 异常重启
                stats['crash'] += 1
                last_boot_time = None 

            elif eid == 1001: # 蓝屏
                stats['bsod'] += 1
                last_boot_time = None

            elif eid == 1: # 唤醒
                stats['wake'] += 1
                stats['hour_dist'][dt.hour] += 1
                
            elif eid == 42: # 睡眠
                stats['sleep'] += 1
                
        except:
            continue
            
    return stats

def get_achievements(stats):
    badges = []
    
    # 1. 铁人勋章
    longest_hours = stats['longest_session']['duration'] / 3600
    if longest_hours > 48:
        badges.append({'icon': '🤖', 'title': '赛博铁人', 'desc': f'单次连续开机 {int(longest_hours)} 小时'})
    elif longest_hours > 12:
        badges.append({'icon': '🔋', 'title': '超长待机', 'desc': f'单次连续工作 {int(longest_hours)} 小时'})
        
    # 2. 熬夜勋章
    late_night_ops = sum(stats['hour_dist'][0:5])
    if late_night_ops > 50:
        badges.append({'icon': '🧛', 'title': '暗夜伯爵', 'desc': '凌晨活跃超过50次'})
    elif late_night_ops == 0:
        badges.append({'icon': '🌞', 'title': '养生达人', 'desc': '从不熬夜，作息极其规律'})
        
    # 3. 稳定勋章
    crash_total = stats['bsod'] + stats['crash']
    if crash_total == 0:
        badges.append({'icon': '🛡️', 'title': '稳如泰山', 'desc': '全年 0 崩溃，简直是奇迹'})
    elif stats['bsod'] > 5:
        badges.append({'icon': '💊', 'title': '蓝屏受害者', 'desc': '经历了太多不该承受的痛苦'})
        
    # 4. 活跃勋章
    total_hours = stats['total_uptime_seconds'] / 3600
    if total_hours > 2000:
        badges.append({'icon': '💻', 'title': '人机合一', 'desc': f'累计陪伴电脑 {int(total_hours)} 小时'})
        
    # 5. 折腾勋章
    if stats['install_count'] > 30:
        badges.append({'icon': '🛠️', 'title': '装机狂魔', 'desc': f'安装/更新了 {stats["install_count"]} 次软件'})

    if not badges:
        badges.append({'icon': '🧘', 'title': '数字隐士', 'desc': '平平淡淡才是真'})
        
    return badges

def generate_html(stats, year):
    badges = get_achievements(stats)
    
    # 数据转换
    total_uptime_hours = stats['total_uptime_seconds'] / 3600
    avg_duration = (total_uptime_hours / len(stats['session_durations'])) if stats['session_durations'] else 0
    
    longest_hours = stats['longest_session']['duration'] / 3600
    longest_date_str = stats['longest_session']['date'].strftime("%m月%d日") if stats['longest_session']['date'] else "无"
    
    latest_time_str = stats['latest_session'].strftime('%H:%M') if stats['latest_session'] else "无"
    latest_date_str = stats['latest_session'].strftime('%m月%d日') if stats['latest_session'] else ""
    
    crash_total = stats['crash'] + stats['bsod']
    
    # 饼图数据
    pie_data = [
        {'value': stats['weekday_activity'], 'name': '工作日搬砖'},
        {'value': stats['weekend_activity'], 'name': '周末狂欢'}
    ]

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>我的 {year} 年度PC使用报告</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">
        <style>
            /* 定义新版配色变量 */
            :root {{ 
                --bg: #0f172a; 
                --card-bg: #1e293b; 
                --card-border: #334155;
                --text-main: #f1f5f9; 
                --text-dim: #94a3b8;
                
                --accent-primary: #818cf8; /* Indigo */
                --accent-secondary: #c084fc; /* Purple */
                --accent-pink: #f472b6; /* Pink */
                
                --danger: #ef4444;
                --gradient-main: linear-gradient(135deg, #6366f1 0%, #ec4899 100%);
            }}
            
            body {{ 
                font-family: 'Noto Sans SC', sans-serif; 
                background-color: var(--bg); 
                background-image: 
                    radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                    radial-gradient(at 100% 0%, rgba(236, 72, 153, 0.15) 0px, transparent 50%);
                color: var(--text-main); 
                margin: 0; 
                padding: 40px 20px; 
                line-height: 1.6; 
            }}
            
            .container {{ max-width: 1100px; margin: 0 auto; }}
            
            /* Header */
            .header {{ 
                text-align: center; 
                padding: 80px 20px; 
                background: rgba(30, 41, 59, 0.5);
                backdrop-filter: blur(10px);
                border-radius: 30px; 
                margin-bottom: 40px; 
                border: 1px solid rgba(255,255,255,0.1);
                box-shadow: 0 20px 50px -12px rgba(0, 0, 0, 0.5);
            }}
            .header h1 {{ 
                margin: 0; 
                font-size: 3.5em; 
                font-weight: 800; 
                background: var(--gradient-main); 
                -webkit-background-clip: text; 
                -webkit-text-fill-color: transparent; 
                letter-spacing: -1px;
            }}
            .header p {{ color: var(--text-dim); margin-top: 15px; font-size: 1.2em; font-weight: 300; }}
            
            /* Cards */
            .card {{ 
                background: var(--card-bg); 
                border-radius: 24px; 
                padding: 35px; 
                margin-bottom: 30px; 
                border: 1px solid var(--card-border); 
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
                border-color: rgba(129, 140, 248, 0.3);
            }}
            .card h2 {{ 
                margin-top: 0; 
                font-size: 1.6em; 
                margin-bottom: 30px; 
                color: #fff; 
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .card h2::before {{
                content: '';
                display: block;
                width: 6px;
                height: 24px;
                background: var(--gradient-main);
                border-radius: 3px;
            }}
            
            /* Badge Grid */
            .badge-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
            .badge {{ 
                background: rgba(255,255,255,0.03); 
                padding: 25px; 
                border-radius: 18px; 
                text-align: center; 
                border: 1px solid rgba(255,255,255,0.05);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            .badge:hover {{ 
                background: rgba(255,255,255,0.08);
                transform: scale(1.05); 
                border-color: var(--accent-primary);
                box-shadow: 0 0 20px rgba(129, 140, 248, 0.2); 
            }}
            .badge-icon {{ font-size: 4em; display: block; margin-bottom: 15px; filter: drop-shadow(0 0 10px rgba(255,255,255,0.2)); }}
            .badge-title {{ font-weight: bold; color: var(--accent-secondary); display: block; margin-bottom: 8px; font-size: 1.1em; }}
            .badge-desc {{ font-size: 0.85em; color: var(--text-dim); line-height: 1.4; }}

            /* Stats Grid */
            .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; text-align: center; }}
            .stat-box {{ 
                background: rgba(15, 23, 42, 0.6); 
                padding: 25px 15px; 
                border-radius: 18px; 
                border: 1px solid rgba(255,255,255,0.05);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }}
            .stat-num {{ font-size: 2.2em; font-weight: 800; color: #fff; line-height: 1; margin-bottom: 5px; }}
            .stat-label {{ font-size: 0.9em; color: var(--text-dim); font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase; }}
            
            /* ⚠️ 重点：崩溃数据特别样式 */
            .stat-box.danger-zone {{
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.3);
            }}
            .stat-num.danger {{ color: var(--danger); text-shadow: 0 0 15px rgba(239, 68, 68, 0.4); }}
            .stat-comment {{ 
                font-size: 0.75em; 
                color: #fca5a5; 
                margin-top: 8px; 
                font-style: italic; 
                opacity: 0.9;
                max-width: 100%;
                line-height: 1.3;
            }}

            /* Highlight Section */
            .highlight-box {{ 
                background: linear-gradient(135deg, rgba(129, 140, 248, 0.1), rgba(192, 132, 252, 0.05)); 
                padding: 30px; 
                border-radius: 18px; 
                border: 1px solid rgba(129, 140, 248, 0.3); 
                margin-top: 25px; 
                position: relative;
                overflow: hidden;
            }}
            .highlight-box::after {{
                content: '🏆';
                position: absolute;
                right: -20px;
                bottom: -20px;
                font-size: 150px;
                opacity: 0.05;
                transform: rotate(-20deg);
            }}
            .highlight-title {{ color: var(--accent-primary); font-weight: bold; font-size: 1.1em; letter-spacing: 1px; text-transform: uppercase; }}
            .highlight-val {{ font-size: 2.2em; font-weight: 800; margin: 15px 0; background: var(--gradient-main); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .highlight-desc {{ font-size: 0.95em; color: var(--text-dim); z-index: 1; position: relative; }}

            /* Charts */
            .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }}
            .chart-box {{ width: 100%; height: 380px; }}
            
            @media (max-width: 768px) {{ .stat-grid, .chart-row {{ grid-template-columns: 1fr; }} .header h1 {{ font-size: 2.5em; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{year} 年度数字足迹</h1>
                <p>Generated by Python System Report</p>
            </div>

            <!-- 1. 成就墙 -->
            <div class="card">
                <h2>🏆 年度成就徽章</h2>
                <div class="badge-grid">
                    {''.join([f'<div class="badge"><span class="badge-icon">{b["icon"]}</span><span class="badge-title">{b["title"]}</span><span class="badge-desc">{b["desc"]}</span></div>' for b in badges])}
                </div>
            </div>

            <!-- 2. 硬核数据 -->
            <div class="card">
                <h2>📟 核心机能统计</h2>
                <div class="stat-grid">
                    <div class="stat-box">
                        <div class="stat-num">{stats['boot']}</div>
                        <div class="stat-label">开机次数</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{int(total_uptime_hours)}h</div>
                        <div class="stat-label">累计运行</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{stats['install_count']}</div>
                        <div class="stat-label">软件安装</div>
                    </div>
                    
                    <!-- 重点修改区域：加入吐槽文本和特殊样式 -->
                    <div class="stat-box danger-zone">
                        <div class="stat-num danger">{crash_total}</div>
                        <div class="stat-label">异常/崩溃</div>
                        <div class="stat-comment">(希望你的文档都保存了😅)</div>
                    </div>
                    <!-- 结束修改 -->
                    
                </div>

                <div class="highlight-box">
                    <div class="highlight-title">🔥 铁人三项纪录 (单次最长连续运行)</div>
                    <div class="highlight-val">{longest_hours:.1f} 小时</div>
                    <div class="highlight-desc">
                        发生于 <strong style="color:var(--text-main)">{longest_date_str}</strong>。
                        平均每次开机你会使用 {avg_duration:.1f} 小时。
                        {f"<br>另外，你最晚的一次关机是在 {latest_date_str} 的 {latest_time_str}，真的是辛苦了。" if stats['latest_session'] else ""}
                    </div>
                </div>
            </div>

            <!-- 3. 图表分析 -->
            <div class="chart-row">
                <div class="card">
                    <h2>🕒 24小时活跃度</h2>
                    <div id="chart-hour" class="chart-box"></div>
                </div>
                <div class="card">
                    <h2>⚖️ 搬砖 vs 摸鱼</h2>
                    <div id="chart-pie" class="chart-box"></div>
                </div>
            </div>
            
            <div class="card">
                <h2>📅 全年周常规律</h2>
                <div id="chart-week" class="chart-box"></div>
            </div>

            <p style="text-align: center; color: #475569; margin-top: 50px; font-size: 0.8em;">
                隐私声明：数据完全在本地处理，不会上传任何服务器。<br>
                Data source: Windows Event Log (System & Application)
            </p>
        </div>

        <script>
            // ECharts 配色同步
            var colorPrimary = '#818cf8';
            var colorSecondary = '#c084fc';
            var colorPink = '#f472b6';
            var colorText = '#cbd5e1';
            var colorSplit = '#334155';
            
            var chartHour = echarts.init(document.getElementById('chart-hour'));
            chartHour.setOption({{
                tooltip: {{ trigger: 'axis', backgroundColor: 'rgba(30, 41, 59, 0.9)', borderColor: '#475569', textStyle: {{ color: '#fff' }} }},
                grid: {{ top: 30, bottom: 20, left: 10, right: 10, containLabel: true }},
                xAxis: {{ 
                    type: 'category', 
                    data: {list(range(24))}, 
                    axisLine:{{lineStyle:{{color: '#475569'}}}},
                    axisLabel: {{ color: colorText }}
                }},
                yAxis: {{ 
                    type: 'value', 
                    splitLine: {{ lineStyle: {{ color: colorSplit, type: 'dashed' }} }},
                    axisLabel: {{ color: colorText }}
                }},
                series: [{{
                    data: {stats['hour_dist']},
                    type: 'bar',
                    itemStyle: {{ 
                        borderRadius: [4, 4, 0, 0], 
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: colorPink }},
                            {{ offset: 1, color: colorPrimary }}
                        ])
                    }},
                    emphasis: {{ itemStyle: {{ color: '#fff' }} }}
                }}]
            }});

            var chartPie = echarts.init(document.getElementById('chart-pie'));
            chartPie.setOption({{
                tooltip: {{ trigger: 'item', backgroundColor: 'rgba(30, 41, 59, 0.9)', textStyle: {{ color: '#fff' }} }},
                legend: {{ bottom: '0', textStyle: {{ color: colorText }} }},
                series: [{{
                    name: '活跃分布',
                    type: 'pie',
                    radius: ['45%', '70%'],
                    itemStyle: {{ borderRadius: 10, borderColor: '#1e293b', borderWidth: 3 }},
                    label: {{ show: false }},
                    data: {json.dumps(pie_data)},
                    color: [colorPrimary, colorSecondary]
                }}]
            }});
            
            var chartWeek = echarts.init(document.getElementById('chart-week'));
            chartWeek.setOption({{
                tooltip: {{ trigger: 'axis', backgroundColor: 'rgba(30, 41, 59, 0.9)', textStyle: {{ color: '#fff' }} }},
                grid: {{ top: 30, bottom: 20, left: 10, right: 10, containLabel: true }},
                xAxis: {{ 
                    type: 'category', 
                    data: ['周一','周二','周三','周四','周五','周六','周日'], 
                    axisLine:{{lineStyle:{{color: '#475569'}}}},
                    axisLabel: {{ color: colorText }}
                }},
                yAxis: {{ 
                    type: 'value', 
                    splitLine: {{ lineStyle: {{ color: colorSplit, type: 'dashed' }} }},
                    axisLabel: {{ color: colorText }}
                }},
                series: [{{
                    data: {stats['weekday_dist']},
                    type: 'line',
                    smooth: true,
                    symbolSize: 8,
                    areaStyle: {{ 
                        opacity: 0.3, 
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: colorSecondary }},
                            {{ offset: 1, color: 'rgba(192, 132, 252, 0)' }}
                        ])
                    }},
                    itemStyle: {{ color: colorSecondary, borderColor: '#fff', borderWidth: 2 }},
                    lineStyle: {{ width: 4, color: colorSecondary }}
                }}]
            }});
            
            window.onresize = function() {{
                chartHour.resize(); chartPie.resize(); chartWeek.resize();
            }};
        </script>
    </body>
    </html>
    """
    
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\n🎉 报告已生成！请查看文件: {HTML_FILE}")
    webbrowser.open('file://' + os.path.abspath(HTML_FILE))

if __name__ == "__main__":
    current_year = datetime.datetime.now().year
    
    try:
        user_input = input(f"请输入要查询的年份 (默认 {current_year}): ")
        target_year = int(user_input) if user_input.strip().isdigit() else current_year
        HTML_FILE = f"my_digital_life_{target_year}.html"
        
        events = get_hybrid_data(target_year)
        if events:
            stats = analyze_hybrid(events)
            generate_html(stats, target_year)
        else:
            print("\n❌ 未能获取数据。")
            print("💡 小贴士：系统日志属于敏感信息，请尝试【右键 -> 以管理员身份运行】此脚本。")
            
    except KeyboardInterrupt:
        print("\n已取消。")
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("程序发生错误，按回车键退出...")