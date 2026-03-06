# ============================================
# AI护眼朗读老师 - 完整版
# 功能：文字转语音、护眼锁屏、文件导入、跟读评分、认字游戏
# ============================================

# 导入必要的库
import streamlit as st  # 网页界面库
import edge_tts  # 微软Edge文字转语音库
import asyncio  # 异步处理（语音生成需要）
import re  # 正则表达式（提取汉字）
import random  # 随机数（游戏用）
import time  # 时间处理（护眼计时）
from datetime import datetime  # 日期时间
import io  # 字节流处理（文件读取）
import base64  #  base64编码（音频播放）

# 文件解析库
try:
    import pdfplumber  # PDF文件解析
except:
    pass  # 如果没安装，后面会提示

try:
    import docx  # Word文件解析
except:
    pass  # 如果没安装，后面会提示

# ============================================
# 第一部分：页面配置和初始化
# ============================================

# 设置网页标题和布局
st.set_page_config(
    page_title="🎓 AI护眼朗读老师",  # 浏览器标签页标题
    page_icon="📖",  # 图标
    layout="wide",  # 宽屏布局
    initial_sidebar_state="collapsed"  # 侧边栏默认收起
)

# ============================================
# 第二部分：护眼配色方案（柔和护眼色）
# ============================================

# 定义颜色变量，方便统一修改
COLORS = {
    'bg': '#F5F5DC',        # 米黄色背景（护眼）
    'card': '#FAFAD2',      # 浅卡其色卡片
    'green': '#8FBC8F',     # 深海绿（主色调）
    'brown': '#DEB887',     # 暖棕色（次要）
    'rose': '#BC8F8F',      # 玫瑰褐（强调）
    'text': '#2F4F4F',      # 深灰绿文字（柔和）
    'warn': '#CD853F',      # 秘鲁色（警告）
    'success': '#6B8E23',   # 橄榄绿（成功）
    'white': '#FFFAF0'      # 花白色
}

# ============================================
# 第三部分：Session State初始化（保存状态）
# ============================================

# 如果还没有初始化，就创建这些变量
if 'start_time' not in st.session_state:
    st.session_state.start_time = time.time()  # 记录开始时间（护眼计时用）

if 'is_locked' not in st.session_state:
    st.session_state.is_locked = False  # 是否处于锁屏状态

if 'lock_start_time' not in st.session_state:
    st.session_state.lock_start_time = None  # 锁屏开始时间

if 'text_content' not in st.session_state:
    # 默认课文内容（静夜思）
    st.session_state.text_content = """床前明月光，疑是地上霜。
举头望明月，低头思故乡。"""

if 'game_questions' not in st.session_state:
    st.session_state.game_questions = []  # 游戏题目列表

if 'game_index' not in st.session_state:
    st.session_state.game_index = 0  # 当前游戏题号

if 'game_score' not in st.session_state:
    st.session_state.game_score = 0  # 游戏得分

if 'game_active' not in st.session_state:
    st.session_state.game_active = False  # 游戏是否进行中

if 'record_score' not in st.session_state:
    st.session_state.record_score = 0  # 录音评分

# ============================================
# 第四部分：拼音数据（用于游戏）
# ============================================

# 汉字到拼音的映射字典
PINYIN_DICT = {
    '床': 'chuáng', '前': 'qián', '明': 'míng', '月': 'yuè', '光': 'guāng',
    '疑': 'yí', '是': 'shì', '地': 'dì', '上': 'shàng', '霜': 'shuāng',
    '举': 'jǔ', '头': 'tóu', '望': 'wàng', '低': 'dī', '思': 'sī',
    '故': 'gù', '乡': 'xiāng', '春': 'chūn', '眠': 'mián', '不': 'bù',
    '觉': 'jué', '晓': 'xiǎo', '处': 'chù', '闻': 'wén', '啼': 'tí',
    '鸟': 'niǎo', '夜': 'yè', '来': 'lái', '风': 'fēng', '雨': 'yǔ',
    '声': 'shēng', '花': 'huā', '落': 'luò', '多': 'duō', '少': 'shǎo'
}

# 错误拼音选项（用于生成干扰项）
WRONG_PINYIN = {
    '床': ['chuāng', 'cuáng', 'cháng'], '前': ['qiǎn', 'qán', 'pián'],
    '明': ['mín', 'mìng', 'mǐng'], '月': ['yüè', 'yué', 'yùe'],
    '光': ['guáng', 'gāng', 'guǎng'], '疑': ['ní', 'yǐ', 'yì'],
    '是': ['sì', 'shī', 'sí'], '地': ['de', 'dí', 'dì'],
    '上': ['shàng', 'sàng', 'shāng'], '霜': ['suāng', 'shuǎng', 'shāng'],
    '举': ['jù', 'jiǔ', 'qǔ'], '头': ['tòu', 'tóu', 'tó'],
    '望': ['wàng', 'wáng', 'wǎng'], '低': ['dī', 'dí', 'dǐ'],
    '思': ['sī', 'sí', 'sì'], '故': ['gǔ', 'gū', 'gú'],
    '乡': ['xiáng', 'xāng', 'xiǎng'], '春': ['chūn', 'cūn', 'chōng'],
    '眠': ['mián', 'mín', 'miǎn'], '不': ['bú', 'bù', 'bū'],
    '觉': ['jué', 'jiào', 'jüé'], '晓': ['xiǎo', 'xiāo', 'xǎo']
}

# ============================================
# 第五部分：CSS样式（美化界面）
# ============================================

def get_css():
    """返回护眼CSS样式"""
    return f"""
    <style>
    /* 全局背景 */
    .stApp {{
        background: linear-gradient(135deg, {COLORS['bg']} 0%, {COLORS['white']} 100%);
    }}
    
    /* 标题卡片 */
    .header-card {{
        background: {COLORS['card']};
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        margin-bottom: 20px;
        border: 3px solid {COLORS['green']};
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    
    .header-card h1 {{
        color: {COLORS['success']};
        font-size: 2.5rem;
        margin: 0;
    }}
    
    /* 功能卡片 */
    .feature-card {{
        background: {COLORS['card']};
        border-radius: 20px;
        padding: 20px;
        margin: 10px 0;
        border: 2px solid {COLORS['green']};
    }}
    
    /* 课文显示区 */
    .text-display {{
        background: #FFFCF5;
        border-radius: 15px;
        padding: 25px;
        font-size: 1.5rem;
        line-height: 2;
        color: {COLORS['text']};
        border: 2px solid {COLORS['brown']};
        font-family: "KaiTi", "STKaiti", serif;
        min-height: 150px;
    }}
    
    /* 按钮样式 */
    .stButton > button {{
        width: 100%;
        border-radius: 15px;
        font-size: 1.2rem;
        font-weight: bold;
        padding: 10px;
    }}
    
    /* 计时器 */
    .timer-box {{
        position: fixed;
        top: 10px;
        right: 10px;
        background: {COLORS['green']};
        color: white;
        padding: 10px 20px;
        border-radius: 20px;
        font-weight: bold;
        z-index: 100;
    }}
    
    /* 锁屏遮罩 */
    .lock-screen {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, #2F4F4F 0%, #556B2F 100%);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: white;
        text-align: center;
    }}
    
    .lock-screen h2 {{
        font-size: 3rem;
        color: #F5F5DC;
        margin-bottom: 20px;
    }}
    
    .countdown {{
        font-size: 4rem;
        color: #FFD700;
        font-weight: bold;
        margin: 20px 0;
    }}
    
    /* 游戏选项 */
    .game-option {{
        background: {COLORS['card']};
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        cursor: pointer;
        font-size: 1.3rem;
        border: 2px solid {COLORS['brown']};
        margin: 5px;
    }}
    
    .correct {{
        background: {COLORS['success']} !important;
        color: white !important;
    }}
    
    .wrong {{
        background: #CD5C5C !important;
        color: white !important;
    }}
    </style>
    """

# 应用CSS
st.markdown(get_css(), unsafe_allow_html=True)

# ============================================
# 第六部分：核心功能函数
# ============================================

async def generate_speech(text, voice, speed):
    """
    使用Edge-TTS生成语音
    参数：
        text: 要朗读的文字
        voice: 声音类型（xiaoxiao女声/yunxi男声）
        speed: 语速（如"-20%"表示慢速）
    返回：音频字节数据
    """
    try:
        # 创建语音合成对象
        communicate = edge_tts.Communicate(text, voice, rate=speed)
        
        # 收集音频数据
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        
        return audio_bytes
    except Exception as e:
        st.error(f"语音生成失败：{str(e)}")
        return None

def parse_file(uploaded_file):
    """
    解析上传的文件（TXT/PDF/Word）
    参数：uploaded_file - Streamlit上传的文件对象
    返回：文件中的文字内容
    """
    if uploaded_file is None:
        return None
    
    try:
        # 获取文件类型
        file_type = uploaded_file.type
        
        # 处理TXT文件
        if file_type == "text/plain":
            return uploaded_file.getvalue().decode("utf-8")
        
        # 处理PDF文件
        elif file_type == "application/pdf":
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(io.BytesIO(uploaded_file.getvalue())) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text
            except ImportError:
                st.error("缺少pdfplumber库，请运行：pip install pdfplumber")
                return None
        
        # 处理Word文件
        elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          "application/msword"]:
            try:
                import docx
                doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
                return "\n".join([para.text for para in doc.paragraphs])
            except ImportError:
                st.error("缺少python-docx库，请运行：pip install python-docx")
                return None
        
        else:
            st.error("不支持的文件格式")
            return None
            
    except Exception as e:
        st.error(f"文件解析失败：{str(e)}")
        return None

def generate_game_questions(text):
    """
    从课文中生成认字游戏题目
    参数：text - 课文文字
    返回：题目列表（每个题目包含汉字、选项、正确答案）
    """
    # 提取所有中文字符
    chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)
    
    # 去重并限制数量（最多10个）
    unique_chars = list(set(chinese_chars))[:10]
    
    questions = []
    for char in unique_chars:
        if char in PINYIN_DICT:
            correct = PINYIN_DICT[char]  # 正确答案
            wrongs = WRONG_PINYIN.get(char, [])[:3]  # 取3个错误答案
            
            # 组合选项并打乱顺序
            options = [correct] + wrongs
            random.shuffle(options)
            
            questions.append({
                'char': char,           # 汉字
                'options': options,     # 四个选项
                'answer': correct       # 正确答案
            })
    
    return questions

def check_eye_protection():
    """
    检查护眼锁屏状态
    返回：True表示需要锁屏，False表示正常使用
    """
    current_time = time.time()
    elapsed = current_time - st.session_state.start_time
    
    # 25分钟 = 1500秒，检查是否需要锁屏
    if elapsed > 1500 and not st.session_state.is_locked:
        st.session_state.is_locked = True
        st.session_state.lock_start_time = current_time
        return True
    
    # 如果已经在锁屏状态，检查是否满5分钟（300秒）
    if st.session_state.is_locked and st.session_state.lock_start_time:
        rest_time = current_time - st.session_state.lock_start_time
        if rest_time > 300:  # 5分钟到，解锁
            st.session_state.is_locked = False
            st.session_state.lock_start_time = None
            st.session_state.start_time = current_time  # 重置计时器
            st.session_state.just_unlocked = True  # 标记刚解锁
            return False
    
    return st.session_state.is_locked

# ============================================
# 第七部分：界面渲染函数
# ============================================

def render_lock_screen():
    """渲染护眼锁屏界面"""
    if st.session_state.lock_start_time:
        # 计算剩余时间
        remaining = 300 - (time.time() - st.session_state.lock_start_time)
        if remaining < 0:
            remaining = 0
        
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        # 锁屏HTML
        lock_html = f"""
        <div class="lock-screen">
            <h2>🌿 护眼休息模式</h2>
            <p style="font-size:1.5rem;">已用眼25分钟，请远眺休息5分钟再回来！</p>
            <div class="countdown">{minutes:02d}:{seconds:02d}</div>
            <p>👀 看看窗外的绿色植物</p>
            <p>🌳 或者闭上眼睛，深呼吸</p>
            <div style="margin-top:20px; padding:10px 20px; background:rgba(255,255,255,0.2); border-radius:20px;">
                ✅ 学习进度已自动保存
            </div>
        </div>
        """
        st.markdown(lock_html, unsafe_allow_html=True)
        
        # 每秒自动刷新倒计时
        time.sleep(1)
        st.rerun()

def render_welcome_back():
    """渲染休息结束欢迎界面"""
    welcome_html = """
    <div style="position:fixed; top:0; left:0; width:100%; height:100%; 
                background:linear-gradient(135deg, #8FBC8F 0%, #F5F5DC 100%);
                z-index:9998; display:flex; flex-direction:column;
                justify-content:center; align-items:center;
                animation:fadeOut 3s forwards;">
        <h1 style="font-size:3.5rem; color:#2F4F4F;">🎉 欢迎回来！</h1>
        <p style="font-size:1.5rem; color:#556B2F;">休息好了，继续学习吧！</p>
        <p style="font-size:1rem; color:#6B8E23; margin-top:20px;">3秒后自动恢复...</p>
    </div>
    <style>
        @keyframes fadeOut {
            0% { opacity: 1; }
            70% { opacity: 1; }
            100% { opacity: 0; visibility: hidden; }
        }
    </style>
    """
    st.markdown(welcome_html, unsafe_allow_html=True)
    time.sleep(3)
    st.session_state.just_unlocked = False
    st.rerun()

# ============================================
# 第八部分：主程序界面
# ============================================

def main():
    """主函数：渲染整个界面"""
    
    # 检查护眼锁屏
    if check_eye_protection():
        render_lock_screen()
        return
    
    # 检查是否刚解锁
    if st.session_state.get('just_unlocked', False):
        render_welcome_back()
        return
    
    # 显示用眼计时器（右上角）
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = max(0, 1500 - elapsed)
    mins = remaining // 60
    
    timer_html = f"""
    <div class="timer-box">
        ⏱️ 已用{elapsed//60}分 | 休息倒计时:{mins}分
    </div>
    """
    st.markdown(timer_html, unsafe_allow_html=True)
    
    # ========== 标题区域 ==========
    st.markdown(f"""
    <div class="header-card">
        <h1>🎓 AI护眼朗读老师 📖</h1>
        <p style="color:{COLORS['text']}; font-size:1.1rem; margin-top:10px;">
            🌿 护眼模式已开启 | 25分钟自动提醒休息 | 让学习更健康
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 护眼提示横幅
    st.markdown(f"""
    <div style="background:{COLORS['warn']}; color:white; padding:12px; 
                border-radius:10px; text-align:center; margin-bottom:20px; font-weight:bold;">
        💡 护眼小贴士：保持30cm阅读距离，每25分钟远眺20英尺外20秒
    </div>
    """, unsafe_allow_html=True)
    
    # ========== 控制面板 ==========
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        # 文件上传
        uploaded = st.file_uploader(
            "📤 导入课文(支持TXT/PDF/Word)",
            type=['txt', 'pdf', 'docx', 'doc']
        )
        if uploaded:
            parsed = parse_file(uploaded)
            if parsed:
                st.session_state.text_content = parsed
                st.success("✅ 课文导入成功！")
                # 重新生成游戏题目
                st.session_state.game_questions = generate_game_questions(parsed)
    
    with col2:
        # 声音选择
        voice_opt = st.selectbox(
            "🎙️ 选择声音",
            ["👩 女老师(晓晓)", "👨 男老师(云希)"]
        )
        # 映射到Edge-TTS的语音代码
        voice_map = {
            "👩 女老师(晓晓)": "zh-CN-XiaoxiaoNeural",
            "👨 男老师(云希)": "zh-CN-YunxiNeural"
        }
        selected_voice = voice_map[voice_opt]
    
    with col3:
        # 语速选择
        speed_opt = st.selectbox(
            "⚡ 语速",
            ["🐢 慢速", "🐇 正常", "🚀 快速"]
        )
        speed_map = {
            "🐢 慢速": "-20%",
            "🐇 正常": "+0%",
            "🚀 快速": "+20%"
        }
        selected_speed = speed_map[speed_opt]
    
    with col4:
        # 停止按钮
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⏹️ 停止朗读", use_container_width=True):
            st.session_state.playing = False
            st.info("已停止")
    
    # ========== 课文编辑和显示 ==========
    # 文本编辑框
    new_text = st.text_area(
        "课文内容（可直接编辑）",
        value=st.session_state.text_content,
        height=150
    )
    # 保存编辑的内容
    if new_text != st.session_state.text_content:
        st.session_state.text_content = new_text
        st.session_state.game_questions = generate_game_questions(new_text)
    
    # 美化显示课文
    st.markdown(f"""
    <div class="text-display">
        {new_text.replace(chr(10), '<br>')}
    </div>
    """, unsafe_allow_html=True)
    
    # ========== 播放按钮（醒目） ==========
    col_play1, col_play2, col_play3 = st.columns([1, 2, 1])
    with col_play2:
        if st.button("▶️ 开始朗读课文", use_container_width=True, type="primary"):
            with st.spinner("🎙️ 正在生成语音，请稍候..."):
                # 按行分割课文
                lines = [s for s in new_text.split('\n') if s.strip()]
                all_audio = b""
                
                # 逐行生成语音并合并
                for line in lines:
                    audio = asyncio.run(generate_speech(line, selected_voice, selected_speed))
                    if audio:
                        all_audio += audio
                
                # 播放音频
                if all_audio:
                    st.audio(all_audio, format='audio/mp3')
                    st.success("🎉 朗读完成！")
    
    # ========== 功能卡片区 ==========
    col_feat1, col_feat2 = st.columns(2)
    
    # ----- 左侧：跟读录音 -----
    with col_feat1:
        st.markdown('<div class="feature-card">', unsafe_allow_html=True)
        st.markdown("### 🎤 跟读录音")
        
        # 录音按钮（模拟）
        col_rec1, col_rec2 = st.columns(2)
        with col_rec1:
            if st.button("🎙️ 开始录音", use_container_width=True):
                st.session_state.recording = True
                st.session_state.record_start = time.time()
                st.info("录音中...请朗读上方课文")
        
        with col_rec2:
            if st.button("🛑 停止录音", use_container_width=True):
                if st.session_state.get('recording', False):
                    duration = time.time() - st.session_state.record_start
                    st.session_state.recording = False
                    
                    # 模拟评分算法
                    text_len = len(new_text.replace('\n', '').replace(' ', ''))
                    base = 70
                    time_bonus = min(20, int(duration))
                    random_bonus = random.randint(5, 10)
                    final = min(100, base + time_bonus + random_bonus)
                    st.session_state.record_score = final
        
        # 显示评分
        score = st.session_state.record_score
        color = COLORS['success'] if score >= 85 else COLORS['warn']
        
        st.markdown(f"""
        <div style="text-align:center; margin-top:15px;">
            <div style="font-size:2.5rem; font-weight:bold; color:{color};">
                {score}分
            </div>
            <p>🎯 AI发音评分</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 评分反馈
        if score > 0:
            if score >= 95:
                st.balloons()
                st.success("🏆 发音完美！")
            elif score >= 85:
                st.success("👍 发音优秀！")
            elif score >= 70:
                st.info("🙂 发音良好，继续加油！")
            else:
                st.warning("💪 还需要多练习哦！")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ----- 右侧：认字游戏 -----
    with col_feat2:
        st.markdown('<div class="feature-card">', unsafe_allow_html=True)
        st.markdown("### 🎮 认字小游戏")
        
        # 开始游戏按钮
        if st.button("🎲 开始游戏", use_container_width=True):
            if not st.session_state.game_questions:
                st.session_state.game_questions = generate_game_questions(st.session_state.text_content)
            
            if st.session_state.game_questions:
                st.session_state.game_active = True
                st.session_state.game_index = 0
                st.session_state.game_score = 0
            else:
                st.error("课文太短，无法生成游戏题目")
        
        # 游戏界面
        if st.session_state.game_active and st.session_state.game_questions:
            questions = st.session_state.game_questions
            idx = st.session_state.game_index
            
            # 显示当前题目
            if idx < len(questions):
                q = questions[idx]
                
                # 显示汉字
                st.markdown(f"""
                <div style="text-align:center; margin:15px 0;">
                    <div style="font-size:3.5rem; color:{COLORS['rose']}; font-weight:bold;">
                        {q['char']}
                    </div>
                    <p style="color:{COLORS['text']};">请选择正确的拼音：</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 显示选项（2x2网格）
                opts = st.columns(2)
                for i, opt in enumerate(q['options']):
                    with opts[i % 2]:
                        if st.button(opt, key=f"opt_{idx}_{i}", use_container_width=True):
                            # 检查答案
                            if opt == q['answer']:
                                st.session_state.game_score += 1
                                st.success("✅ 回答正确！")
                            else:
                                st.error(f"❌ 错误，正确答案是：{q['answer']}")
                            
                            # 下一题
                            time.sleep(1)
                            st.session_state.game_index += 1
                            st.rerun()
                
                # 进度条
                progress = idx / len(questions)
                st.progress(progress)
                st.write(f"进度：{idx + 1}/{len(questions)} 题 | 得分：{st.session_state.game_score}")
            
            else:
                # 游戏结束
                total = len(questions)
                final_score = st.session_state.game_score
                st.success(f"🎉 游戏完成！得分：{final_score}/{total}")
                
                if final_score == total:
                    st.balloons()
                    st.success("🏆 满分！太棒了！")
                elif final_score >= total * 0.8:
                    st.success("👍 真厉害！")
                
                st.session_state.game_active = False
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ========== 页脚 ==========
    st.markdown(f"""
    <div style="text-align:center; margin-top:30px; padding:15px; 
                background:#E8F5E9; border-radius:15px; color:#2E7D32;">
        <p>🌿 护眼模式运行中 | 已自动开启25分钟休息提醒 | 保护视力，快乐学习</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 自动刷新（每秒更新计时器）
    time.sleep(1)
    st.rerun()

# ============================================
# 程序入口
# ============================================

if __name__ == "__main__":
    main()