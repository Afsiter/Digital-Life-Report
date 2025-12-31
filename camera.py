import os
import sys
import datetime
import json
import webbrowser
from collections import Counter, defaultdict
from PIL import Image, ExifTags

# ================= 配置区 =================
# 输出文件名
OUTPUT_HTML = "my_photo_life_report.html"
# ========================================

def get_exif_data(image_path):
    """
    读取单张图片的EXIF信息，进行清洗和格式化
    """
    try:
        img = Image.open(image_path)
        exif_raw = img._getexif()
        if not exif_raw:
            return None
            
        # 将数字ID转换为标签名
        exif = {
            ExifTags.TAGS.get(k, k): v
            for k, v in exif_raw.items()
        }
        
        data = {}
        
        # 1. 焦段处理 (FocalLength) - 需求核心：无信息默认14mm
        fl = exif.get('FocalLength')
        try:
            if fl:
                # 兼容旧版Pillow返回分数/元组的情况
                if isinstance(fl, tuple):
                    val = float(fl[0]) / float(fl[1]) if fl[1] != 0 else 0
                else:
                    val = float(fl)
                data['FocalLength'] = int(round(val))
            else:
                data['FocalLength'] = 14 # 默认设定
        except:
            data['FocalLength'] = 14

        # 2. 时间处理 (DateTimeOriginal)
        date_str = exif.get('DateTimeOriginal')
        if date_str:
            try:
                # 常见格式: 2023:12:30 10:20:30
                dt = datetime.datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                data['Month'] = dt.month
                data['Hour'] = dt.hour
                data['Year'] = dt.year
                data['DateObject'] = dt
            except:
                return None
        else:
            return None

        # 3. 快门速度 (ExposureTime)
        exp = exif.get('ExposureTime')
        if exp:
            try:
                val = float(exp)
                if val < 1.0:
                    denom = int(round(1/val))
                    data['ShutterSpeed'] = f"1/{denom}s"
                    data['ShutterVal'] = val
                else:
                    data['ShutterSpeed'] = f"{val}s"
                    data['ShutterVal'] = val
            except:
                data['ShutterSpeed'] = "Unknown"
        else:
            data['ShutterSpeed'] = "Unknown"

        # 4. 光圈 (FNumber)
        f_num = exif.get('FNumber')
        if f_num:
            try:
                val = float(f_num)
                data['Aperture'] = f"f/{val:.1f}"
                data['ApertureVal'] = val
            except:
                data['Aperture'] = "Unknown"
        else:
            data['Aperture'] = "Unknown"

        # 5. 器材信息 (Model)
        data['Camera'] = exif.get('Model', 'Unknown Camera').strip().replace('\x00', '')
        
        # 6. ISO
        data['ISO'] = int(exif.get('ISOSpeedRatings', 0))

        return data

    except Exception:
        return None

def scan_folders(folder_paths):
    print("🕵️‍♂️ 正在扫描文件夹...")
    print("   [1/3] 正在解析图像 EXIF 元数据...")
    
    photos = []
    valid_extensions = ('.jpg', '.jpeg')

    for folder_path in folder_paths:
        print(f"   ---> 扫描路径: {folder_path}")
        for root, _, files in os.walk(folder_path):
            for filename in files:
                if filename.lower().endswith(valid_extensions):
                    full_path = os.path.join(root, filename)
                    data = get_exif_data(full_path)
                    if data:
                        photos.append(data)
    
    return photos

def analyze_data(photos):
    print("   [2/3] 正在生成统计分布...")
    if not photos:
        return None
        
    stats = {
        'total_count': len(photos),
        'focal_dist': Counter(),
        'month_dist': [0] * 12, # 0-11 index
        'hour_dist': [0] * 24,
        'camera_dist': Counter(),
        'shutter_dist': Counter(),
        'aperture_dist': Counter(),
        'iso_dist': [],
        'latest_photo': None,
        'earliest_photo': None,
        'primary_camera': "None"
    }
    
    dates = []
    
    for p in photos:
        stats['focal_dist'][p['FocalLength']] += 1
        stats['month_dist'][p['Month']-1] += 1
        stats['hour_dist'][p['Hour']] += 1
        stats['camera_dist'][p['Camera']] += 1
        if p.get('ShutterSpeed') != 'Unknown':
            stats['shutter_dist'][p['ShutterSpeed']] += 1
        if p.get('Aperture') != 'Unknown':
            stats['aperture_dist'][p['Aperture']] += 1
        
        stats['iso_dist'].append(p['ISO'])
        dates.append(p['DateObject'])

    if dates:
        dates.sort()
        stats['earliest_photo'] = dates[0]
        stats['latest_photo'] = dates[-1]

    if stats['camera_dist']:
        stats['primary_camera'] = stats['camera_dist'].most_common(1)[0][0]

    return stats

def get_achievements(stats):
    print("   [3/3] 正在评估摄影成就徽章...")
    badges = []
    
    total = stats['total_count']
    if total == 0: return []

    # 1. 焦段偏好
    focals = stats['focal_dist']
    wide_count = sum(c for f, c in focals.items() if f < 24)
    tele_count = sum(c for f, c in focals.items() if f >= 85)
    
    if wide_count / total > 0.4:
        badges.append({'icon': '🏔️', 'title': '广角狂魔', 'desc': '40% 以上的照片使用了超广角，心中装得下山河湖海'})
    elif tele_count / total > 0.4:
        badges.append({'icon': '🔭', 'title': '空气切割机', 'desc': '偏爱长焦压缩感，也是一名合格的偷窥...观察者'})
    else:
        badges.append({'icon': '👁️', 'title': '人文之眼', 'desc': '多使用 35mm-50mm 标准焦段，平实记录生活'})

    # 2. 作息偏好
    night_shots = sum(stats['hour_dist'][0:5]) + sum(stats['hour_dist'][22:24])
    noon_shots = sum(stats['hour_dist'][11:14])
    
    if night_shots / total > 0.3:
        badges.append({'icon': '🌃', 'title': '夜之城行者', 'desc': '超过 30% 的照片拍摄于深夜，ISO 一定很高吧'})
    elif noon_shots / total > 0.4:
        badges.append({'icon': '☀️', 'title': '光影捕手', 'desc': '顶着正午的大太阳拍摄，你是真的不怕热'})
        
    # 3. 光圈偏好
    apertures = stats['aperture_dist']
    large_aperture = 0
    # 简单的字符串判断 f/1.x or f/2.x
    for k, v in apertures.items():
        try:
            val = float(k.replace('f/', ''))
            if val <= 2.8: large_aperture += v
        except: pass
        
    if large_aperture / total > 0.5:
        badges.append({'icon': '🥯', 'title': '虚化大师', 'desc': '一半以上的照片都在追求焦外如奶油般化开'})
    else:
        badges.append({'icon': '🏔️', 'title': '小光圈战士', 'desc': 'F8 才是风光狗的归宿，边缘画质必须锐利'})

    # 4. 快门数
    if total > 5000:
        badges.append({'icon': '🔫', 'title': '机关枪手', 'desc': f'单文件夹扫射了 {total} 张照片，硬盘还好吗？'})
    elif total < 100:
        badges.append({'icon': '🎨', 'title': '胶片节奏', 'desc': '按快门非常克制，每一张都是深思熟虑'})
        
    # 5. 器材党
    if len(stats['camera_dist']) > 3:
        badges.append({'icon': '📸', 'title': '器材抚摸党', 'desc': f'使用了 {len(stats["camera_dist"])} 种不同的相机拍摄'})

    return badges

def generate_html(stats):
    badges = get_achievements(stats)
    
    # 准备图表数据
    
    # 1. 焦段 (Bar) - 按焦距排序
    sorted_focal = sorted(stats['focal_dist'].items())
    focal_x = [f"{k}mm" for k, v in sorted_focal]
    focal_y = [v for k, v in sorted_focal]
    
    # 2. 月份 (Line)
    month_data = stats['month_dist']
    
    # 3. 时段 (Bar/Polar)
    hour_data = stats['hour_dist']
    
    # 4. 快门 (Top 10)
    sorted_shutter = stats['shutter_dist'].most_common(10)
    # 按快门速度本身排序比较难，这里按数量排序展示热门快门
    shutter_x = [k for k, v in sorted_shutter]
    shutter_y = [v for k, v in sorted_shutter]
    
    # 5. 光圈 (Top 10)
    sorted_aperture = sorted(stats['aperture_dist'].items(), key=lambda x: float(x[0].replace('f/','')) if 'f/' in x[0] else 99)
    aperture_x = [k for k, v in sorted_aperture]
    aperture_y = [v for k, v in sorted_aperture]
    
    # 6. 相机 (Pie)
    pie_data = [{'value': v, 'name': k} for k, v in stats['camera_dist'].items()]

    # 格式化日期
    date_range = "N/A"
    if stats['earliest_photo']:
        d1 = stats['earliest_photo'].strftime("%Y.%m.%d")
        d2 = stats['latest_photo'].strftime("%Y.%m.%d")
        date_range = f"{d1} - {d2}"

    # 平均ISO
    avg_iso = int(sum(stats['iso_dist']) / len(stats['iso_dist'])) if stats['iso_dist'] else 0

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>年度摄影报告 - Digital Lens</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;700&display=swap" rel="stylesheet">
        <style>
            /* 沿用参考脚本的配色，调整为更适合摄影的 Cyan/Orange 风格 */
            :root {{ 
                --bg: #0f172a; 
                --card-bg: #1e293b; 
                --card-border: #334155;
                --text-main: #f1f5f9; 
                --text-dim: #94a3b8;
                
                --accent-primary: #06b6d4; /* Cyan */
                --accent-secondary: #f97316; /* Orange */
                --accent-purple: #8b5cf6; /* Purple */
                
                --danger: #ef4444;
                --gradient-main: linear-gradient(135deg, #06b6d4 0%, #f97316 100%);
            }}
            
            body {{ 
                font-family: 'Noto Sans SC', sans-serif; 
                background-color: var(--bg); 
                background-image: 
                    radial-gradient(at 0% 0%, rgba(6, 182, 212, 0.15) 0px, transparent 50%),
                    radial-gradient(at 100% 100%, rgba(249, 115, 22, 0.15) 0px, transparent 50%);
                color: var(--text-main); 
                margin: 0; 
                padding: 40px 20px; 
                line-height: 1.6; 
            }}
            
            .container {{ max-width: 1200px; margin: 0 auto; }}
            
            /* Header */
            .header {{ 
                text-align: center; 
                padding: 60px 20px; 
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
            .header p {{ color: var(--text-dim); margin-top: 15px; font-size: 1.2em; }}
            
            /* Cards */
            .card {{ 
                background: var(--card-bg); 
                border-radius: 24px; 
                padding: 30px; 
                margin-bottom: 30px; 
                border: 1px solid var(--card-border); 
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s;
            }}
            .card:hover {{ transform: translateY(-2px); border-color: rgba(6, 182, 212, 0.3); }}
            .card h2 {{ 
                margin-top: 0; 
                font-size: 1.5em; 
                margin-bottom: 25px; 
                color: #fff; 
                display: flex; align-items: center; gap: 10px;
            }}
            .card h2::before {{
                content: ''; display: block; width: 6px; height: 24px;
                background: var(--gradient-main); border-radius: 3px;
            }}
            
            /* Badge Grid */
            .badge-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }}
            .badge {{ 
                background: rgba(255,255,255,0.03); 
                padding: 20px; 
                border-radius: 18px; 
                text-align: center; 
                border: 1px solid rgba(255,255,255,0.05);
            }}
            .badge:hover {{ background: rgba(255,255,255,0.08); border-color: var(--accent-primary); }}
            .badge-icon {{ font-size: 3.5em; display: block; margin-bottom: 10px; }}
            .badge-title {{ font-weight: bold; color: var(--accent-primary); display: block; margin-bottom: 5px; }}
            .badge-desc {{ font-size: 0.85em; color: var(--text-dim); }}

            /* Stats Grid */
            .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; text-align: center; margin-bottom: 20px; }}
            .stat-box {{ 
                background: rgba(15, 23, 42, 0.6); 
                padding: 20px; 
                border-radius: 18px; 
                border: 1px solid rgba(255,255,255,0.05);
            }}
            .stat-num {{ font-size: 2em; font-weight: 800; color: #fff; margin-bottom: 5px; }}
            .stat-label {{ font-size: 0.8em; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px; }}

            /* Highlight Box */
            .highlight-box {{ 
                background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(249, 115, 22, 0.05)); 
                padding: 25px; 
                border-radius: 18px; 
                border: 1px solid rgba(6, 182, 212, 0.3); 
                position: relative; overflow: hidden;
            }}
            .highlight-val {{ font-size: 1.8em; font-weight: 800; margin: 10px 0; color: var(--accent-primary); }}
            
            /* Chart Layouts */
            .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }}
            .chart-box {{ width: 100%; height: 350px; }}
            .chart-wide {{ width: 100%; height: 400px; }}
            
            @media (max-width: 768px) {{ .stat-grid, .chart-row {{ grid-template-columns: 1fr; }} .header h1 {{ font-size: 2.5em; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>年度摄影足迹</h1>
                <p>Recorded by Your Camera · Generated by Python</p>
            </div>

            <!-- 1. 核心统计 -->
            <div class="card">
                <h2>📟 核心快门数据</h2>
                <div class="stat-grid">
                    <div class="stat-box">
                        <div class="stat-num">{stats['total_count']}</div>
                        <div class="stat-label">照片总数</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{len(stats['camera_dist'])}</div>
                        <div class="stat-label">使用相机数</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-num">{avg_iso}</div>
                        <div class="stat-label">平均 ISO</div>
                    </div>
                    <div class="stat-box" style="border-color: rgba(249, 115, 22, 0.3); background: rgba(249, 115, 22, 0.1);">
                        <div class="stat-num" style="color: var(--accent-secondary)">JPG</div>
                        <div class="stat-label">文件格式</div>
                    </div>
                </div>
                
                <div class="highlight-box">
                    <div style="font-weight:bold; color:var(--text-dim)">📸 主力生产力工具</div>
                    <div class="highlight-val">{stats['primary_camera']}</div>
                    <div style="font-size: 0.9em; color: var(--text-dim)">
                        记录时间跨度：{date_range}
                    </div>
                </div>
            </div>

            <!-- 2. 成就墙 -->
            <div class="card">
                <h2>🏆 摄影师风格画像</h2>
                <div class="badge-grid">
                    {''.join([f'<div class="badge"><span class="badge-icon">{b["icon"]}</span><span class="badge-title">{b["title"]}</span><span class="badge-desc">{b["desc"]}</span></div>' for b in badges])}
                </div>
            </div>

            <!-- 3. 图表区域 -->
            
            <!-- 焦段与月份 -->
            <div class="card">
                <h2>🔭 焦段统计 (无Exif默认为14mm)</h2>
                <div id="chart-focal" class="chart-wide"></div>
            </div>

            <div class="chart-row">
                <div class="card">
                    <h2>📅 月份活跃度</h2>
                    <div id="chart-month" class="chart-box"></div>
                </div>
                <div class="card">
                    <h2>🕓 拍摄时段 (24H)</h2>
                    <div id="chart-hour" class="chart-box"></div>
                </div>
            </div>
            
            <!-- 参数统计 -->
            <div class="chart-row">
                <div class="card">
                    <h2>⚡ 快门速度 (Top 10)</h2>
                    <div id="chart-shutter" class="chart-box"></div>
                </div>
                <div class="card">
                    <h2>⭕ 光圈分布</h2>
                    <div id="chart-aperture" class="chart-box"></div>
                </div>
            </div>
            
            <!-- 自行发挥：相机型号 -->
            <div class="card">
                <h2>📷 器材使用占比</h2>
                <div id="chart-camera" class="chart-wide" style="height:300px"></div>
            </div>

        </div>

        <script>
            var colorPrimary = '#06b6d4';
            var colorSecondary = '#f97316';
            var colorText = '#cbd5e1';
            var colorSplit = '#334155';
            
            // 1. 焦段图表
            var chartFocal = echarts.init(document.getElementById('chart-focal'));
            chartFocal.setOption({{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ 
                    type: 'category', 
                    data: {json.dumps(focal_x)},
                    axisLabel: {{ color: colorText, rotate: 45 }}
                }},
                yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colorSplit, type: 'dashed' }} }} }},
                series: [{{
                    data: {json.dumps(focal_y)},
                    type: 'bar',
                    itemStyle: {{ 
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: colorPrimary }},
                            {{ offset: 1, color: 'rgba(6, 182, 212, 0.1)' }}
                        ]),
                        borderRadius: [4, 4, 0, 0]
                    }}
                }}]
            }});

            // 2. 月份图表
            var chartMonth = echarts.init(document.getElementById('chart-month'));
            chartMonth.setOption({{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ 
                    type: 'category', 
                    data: ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'],
                    axisLabel: {{ color: colorText }}
                }},
                yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colorSplit, type: 'dashed' }} }} }},
                series: [{{
                    data: {json.dumps(month_data)},
                    type: 'line',
                    smooth: true,
                    areaStyle: {{ opacity: 0.3, color: colorSecondary }},
                    itemStyle: {{ color: colorSecondary }},
                    lineStyle: {{ width: 3 }}
                }}]
            }});

            // 3. 时段图表 (极坐标)
            var chartHour = echarts.init(document.getElementById('chart-hour'));
            chartHour.setOption({{
                tooltip: {{ trigger: 'item' }},
                polar: {{ radius: [30, '80%'] }},
                angleAxis: {{ type: 'category', data: {json.dumps([str(i) for i in range(24)])}, startAngle: 90 }},
                radiusAxis: {{ min: 0 }},
                series: [{{
                    type: 'bar',
                    data: {json.dumps(hour_data)},
                    coordinateSystem: 'polar',
                    itemStyle: {{ color: '#8b5cf6' }}
                }}]
            }});
            
            // 4. 快门图表
            var chartShutter = echarts.init(document.getElementById('chart-shutter'));
            chartShutter.setOption({{
                tooltip: {{ trigger: 'axis' }},
                grid: {{ containLabel: true, left: 10, right: 10, bottom: 10, top: 20 }},
                xAxis: {{ type: 'value', splitLine: {{ show: false }} }},
                yAxis: {{ 
                    type: 'category', 
                    data: {json.dumps(shutter_x)},
                    axisLabel: {{ color: colorText }}
                }},
                series: [{{
                    type: 'bar',
                    data: {json.dumps(shutter_y)},
                    itemStyle: {{ borderRadius: [0, 4, 4, 0], color: colorSecondary }}
                }}]
            }});
            
            // 5. 光圈图表
            var chartAperture = echarts.init(document.getElementById('chart-aperture'));
            chartAperture.setOption({{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ type: 'category', data: {json.dumps(aperture_x)}, axisLabel: {{ color: colorText }} }},
                yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: colorSplit }} }} }},
                series: [{{
                    type: 'bar',
                    data: {json.dumps(aperture_y)},
                    itemStyle: {{ color: colorPrimary }}
                }}]
            }});

            // 6. 相机饼图
            var chartCamera = echarts.init(document.getElementById('chart-camera'));
            chartCamera.setOption({{
                tooltip: {{ trigger: 'item' }},
                series: [{{
                    type: 'pie',
                    radius: ['40%', '70%'],
                    itemStyle: {{ borderRadius: 10, borderColor: '#1e293b', borderWidth: 2 }},
                    data: {json.dumps(pie_data)}
                }}]
            }});

            window.onresize = function() {{
                chartFocal.resize(); chartMonth.resize(); chartHour.resize(); 
                chartShutter.resize(); chartAperture.resize(); chartCamera.resize();
            }};
        </script>
    </body>
    </html>
    """
    
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\n🎉 报告已生成！文件路径: {os.path.abspath(OUTPUT_HTML)}")
    webbrowser.open('file://' + os.path.abspath(OUTPUT_HTML))

if __name__ == "__main__":
    try:
        # 获取用户输入
        print("📸 欢迎使用 Photo Life Annual Report Generator")
        target_folders = input("请输入包含 JPG 图片的文件夹路径（多个路径用逗号分隔）: ").strip()
        
        # 处理引号问题 (Windows复制路径常带引号)
        folder_paths = [path.strip().strip('"').strip("'") for path in target_folders.split(',')]
        
        # 检查路径有效性
        valid_paths = [path for path in folder_paths if os.path.exists(path)]
        if not valid_paths:
            print("❌ 没有提供有效的文件夹路径，请检查后重试。")
        else:
            photos = scan_folders(valid_paths)
            if photos:
                stats = analyze_data(photos)
                generate_html(stats)
            else:
                print("⚠️ 未找到有效的 JPG 图片。")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("程序发生错误，按回车键退出...")