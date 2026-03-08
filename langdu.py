# ============================================
# AI双语朗读老师 - 云端部署最终版
# 适配：Streamlit Cloud/Render/Heroku/GitHub托管
# 特性：多用户访问、手机适配、无本地文件依赖、内存流播放
# ============================================

import streamlit as st
import edge_tts
import asyncio
import time
import re
import uuid
from io import BytesIO
from typing import Optional

# ============================================
# 页面基础配置（适配手机）
# ============================================
st.set_page_config(
    page_title="AI双语朗读老师",
    page_icon="📖",
    layout="centered",  # 手机适配：居中布局
    initial_sidebar_state="collapsed"
)

# ============================================
# Session State 初始化（多用户隔离）
# ============================================
def init_session_state():
    # 生成唯一用户ID（隔离多用户数据）
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    
    defaults = {
        'start_time': time.time(),
        'is_locked': False,
        'lock_start_time': None,
        'current_lang': "en",
        'current_voice': "female",
        'current_lesson': "英语示例（九年级）",
        'display_text': "",
        'current_annotations': {},
        'record_level': "",
        'current_sentence': 0,
        'just_unlocked': False,
        'recording': False,
        'record_start': 0,
        'recording_duration': 0,
        'file_uploaded': False,
        'uploaded_file_data': None,
        'text_area_key': 0,
        'last_uploaded_filename': None,
        'audio_playing': False,  # 音频播放状态
        'loading_audio': False   # 音频加载状态
    }
    
    # 初始化默认课文（避免首次加载为空）
    if 'display_text' not in st.session_state or st.session_state.display_text == "":
        defaults['display_text'] = """Learning English is very important for us. Here are some useful tips.
First, you should listen to English tapes and songs every day. This helps improve your listening skills.
Second, don't be afraid to speak English in public. Practice makes perfect.
Third, reading English newspapers and magazines can enlarge your vocabulary.
Fourth, keeping a diary in English is a good way to improve writing.
Finally, if you have problems, ask your teacher or classmates for help.
Remember, where there is a will, there is a way."""
        defaults['current_annotations'] = {
            "tips": "n. 建议，窍门",
            "improve": "v. 提高，改善",
            "skills": "n. 技能",
            "afraid": "adj. 害怕的",
            "public": "n. 公众，公共场所",
            "Practice": "n. 练习（谚语：熟能生巧）",
            "enlarge": "v. 扩大，增加",
            "vocabulary": "n. 词汇量",
            "diary": "n. 日记",
            "Finally": "adv. 最后",
            "classmates": "n. 同学",
            "Remember": "v. 记住",
            "will": "n. 意志，决心"
        }
    
    # 初始化Session State
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ============================================
# 配色方案（适配手机显示）
# ============================================
COLORS = {
    'bg': '#F5F5F0',
    'card': '#FAFAF5',
    'green': '#5A8F5A',
    'blue': '#4A7AC8',
    'text': '#2C3E50',
    'warn': '#D4A017',
    'success': '#4A9A4A',
    'white': '#FFFFFF',
    'border': '#D0D8D0',
    'tooltip': '#FFF8DC',
    'header': '#E8F0E8'
}

# ============================================
# 示例课文库
# ============================================
EXAMPLE_LIBRARY_ZH = {
    "语文示例-沁园春·雪（九年级上册）": {
        "content": """北国风光，千里冰封，万里雪飘。
望长城内外，惟余莽莽；大河上下，顿失滔滔。
山舞银蛇，原驰蜡象，欲与天公试比高。
须晴日，看红装素裹，分外妖娆。
江山如此多娇，引无数英雄竞折腰。
惜秦皇汉武，略输文采；唐宗宋祖，稍逊风骚。
一代天骄，成吉思汗，只识弯弓射大雕。
俱往矣，数风流人物，还看今朝。""",
        "annotations": {
            "北国": "名词，指中国北方",
            "风光": "名词，风景",
            "冰封": "动词，被冰雪覆盖",
            "雪飘": "动词，雪花飞舞",
            "惟余": "副词，只剩下",
            "莽莽": "形容词，无边无际",
            "顿失": "副词，立刻失去",
            "滔滔": "形容词，水势浩大",
            "银蛇": "名词，像银蛇一样",
            "蜡象": "名词，像白象一样",
            "天公": "名词，老天爷",
            "妖娆": "形容词，娇艳美好",
            "多娇": "形容词，十分娇美",
            "折腰": "动词，弯腰行礼，倾倒",
            "文采": "名词，文学才华",
            "风骚": "名词，文学才华（风指诗经，骚指离骚）",
            "天骄": "名词，天之骄子",
            "俱往矣": "副词，都过去了",
            "风流": "形容词，杰出不凡"
        }
    },
    "语文示例-静夜思（一年级）": {
        "content": """床前明月光，
疑是地上霜。
举头望明月，
低头思故乡。""",
        "annotations": {
            "床前": "名词，床的前面",
            "明月": "名词，明亮的月亮",
            "光": "名词，光线",
            "疑是": "动词，怀疑是",
            "地上": "名词，地面上",
            "霜": "名词，霜",
            "举头": "动词，抬起头",
            "望": "动词，看",
            "低头": "动词，低下头",
            "思": "动词，思念",
            "故乡": "名词，家乡"
        }
    }
}

EXAMPLE_LIBRARY_EN = {
    "英语示例（九年级）": {
        "content": """Learning English is very important for us. Here are some useful tips.
First, you should listen to English tapes and songs every day. This helps improve your listening skills.
Second, don't be afraid to speak English in public. Practice makes perfect.
Third, reading English newspapers and magazines can enlarge your vocabulary.
Fourth, keeping a diary in English is a good way to improve writing.
Finally, if you have problems, ask your teacher or classmates for help.
Remember, where there is a will, there is a way.""",
        "annotations": {
            "tips": "n. 建议，窍门",
            "improve": "v. 提高，改善",
            "skills": "n. 技能",
            "afraid": "adj. 害怕的",
            "public": "n. 公众，公共场所",
            "Practice": "n. 练习（谚语：熟能生巧）",
            "enlarge": "v. 扩大，增加",
            "vocabulary": "n. 词汇量",
            "diary": "n. 日记",
            "Finally": "adv. 最后",
            "classmates": "n. 同学",
            "Remember": "v. 记住",
            "will": "n. 意志，决心"
        }
    },
    "英语示例（三年级）": {
        "content": """Hello! My name is Tom.
I am a student. I am seven years old.
I like to read books and play football.
My favorite color is blue.
I go to school every day.
I love my family and my friends.""",
        "annotations": {
            "Hello": "int. 你好",
            "name": "n. 名字",
            "student": "n. 学生",
            "years old": "年龄表达",
            "like": "v. 喜欢",
            "read": "v. 阅读",
            "play": "v. 玩",
            "favorite": "adj. 最喜欢的",
            "color": "n. 颜色",
            "school": "n. 学校",
            "family": "n. 家庭",
            "friends": "n. 朋友"
        }
    }
}

# ============================================
# 内置常用词典
# ============================================
BUILTIN_DICT_ZH = {
    "之": "助词，的/主谓之间取消句子独立性",
    "其": "代词，他的/那/其中的",
    "而": "连词，表并列/转折/修饰",
    "以": "介词，用/因为/把",
    "于": "介词，在/到/比/被",
    "者": "助词，……的人/……的原因",
    "所": "助词，与动词结合成名词性短语",
    "乃": "副词，于是/才/竟然",
    "且": "连词，况且/而且",
    "因": "介词，于是/凭借/趁着",
    "为": "介词，为了/被/作为",
    "则": "连词，就/那么",
    "故": "连词，所以",
    "虽": "连词，虽然",
    "然": "连词/形容词词尾，然而/……的样子",
    "若": "连词/动词，如果/像",
    "如": "连词/动词，如果/像",
    "使": "连词/动词，假使/让",
    "令": "连词/动词，假使/让",
    "曰": "动词，说",
    "云": "动词，说",
    "行": "动词，走/实行",
    "走": "动词，跑",
    "去": "动词，离开",
    "入": "动词，进入",
    "出": "动词，出去",
    "见": "动词，看见/拜见/被",
    "视": "动词，看",
    "望": "动词，远看/盼望",
    "观": "动词，看/观赏",
    "读": "动词，阅读",
    "学": "动词，学习",
    "思": "动词，思考",
    "知": "动词，知道/了解",
    "人": "名词，人物/人们",
    "民": "名词，百姓",
    "士": "名词，读书人/武士",
    "君": "名词，君主/您",
    "臣": "名词，臣子",
    "父": "名词，父亲",
    "母": "名词，母亲",
    "子": "名词，儿子/您",
    "师": "名词，老师",
    "友": "名词，朋友",
    "天": "名词，天空/上天",
    "地": "名词，大地",
    "山": "名词，山",
    "水": "名词，水",
    "日": "名词，太阳/白天",
    "月": "名词，月亮",
    "风": "名词，风",
    "雨": "名词，雨",
    "花": "名词，花朵",
    "木": "名词，树木",
    "大": "形容词，大的",
    "小": "形容词，小的",
    "多": "形容词，数量大",
    "少": "形容词，数量小",
    "高": "形容词，高度大",
    "深": "形容词，深度大",
    "远": "形容词，距离远",
    "近": "形容词，距离近",
    "新": "形容词，新鲜的",
    "旧": "形容词，陈旧的",
    "美": "形容词，美丽的",
    "善": "形容词，好的/善良的",
    "恶": "形容词，坏的/丑陋的",
    "难": "形容词，困难的",
    "易": "形容词，容易的",
    "不": "副词，否定",
    "无": "副词，没有",
    "未": "副词，还没有",
    "已": "副词，已经",
    "既": "副词，已经",
    "方": "副词，正在/才",
    "正": "副词，正好",
    "必": "副词，一定",
    "定": "副词，必定",
    "诚": "副词，确实",
    "信": "副词，确实",
    "果": "副词，果然",
    "竟": "副词，竟然",
    "卒": "副词，终于",
    "终": "副词，最终",
    "与": "连词，和/同",
    "及": "连词，和",
    "并": "连词，并且",
}

BUILTIN_DICT_EN = {
    "be": "v. 是/存在",
    "have": "v. 有/吃",
    "do": "v. 做/助动词",
    "say": "v. 说",
    "get": "v. 得到/变得",
    "make": "v. 制作/使",
    "go": "v. 去",
    "know": "v. 知道",
    "take": "v. 拿/花费",
    "see": "v. 看见",
    "come": "v. 来",
    "think": "v. 想/认为",
    "look": "v. 看",
    "want": "v. 想要",
    "give": "v. 给",
    "use": "v. 使用",
    "find": "v. 找到",
    "tell": "v. 告诉",
    "ask": "v. 问",
    "work": "v. 工作",
    "seem": "v. 似乎",
    "feel": "v. 感觉",
    "try": "v. 尝试",
    "leave": "v. 离开",
    "call": "v. 打电话/称呼",
    "time": "n. 时间",
    "person": "n. 人",
    "year": "n. 年",
    "way": "n. 方式/路",
    "day": "n. 天",
    "thing": "n. 事情",
    "man": "n. 男人/人类",
    "world": "n. 世界",
    "life": "n. 生活/生命",
    "hand": "n. 手",
    "part": "n. 部分",
    "child": "n. 孩子",
    "eye": "n. 眼睛",
    "woman": "n. 女人",
    "place": "n. 地方",
    "week": "n. 星期",
    "case": "n. 情况/案例",
    "point": "n. 点/观点",
    "government": "n. 政府",
    "company": "n. 公司",
    "good": "adj. 好的",
    "new": "adj. 新的",
    "first": "adj. 第一的",
    "last": "adj. 最后的",
    "long": "adj. 长的",
    "great": "adj. 伟大的",
    "little": "adj. 小的/少的",
    "own": "adj. 自己的",
    "other": "adj. 其他的",
    "old": "adj. 老的/旧的",
    "right": "adj. 正确的/右的",
    "big": "adj. 大的",
    "high": "adj. 高的",
    "different": "adj. 不同的",
    "small": "adj. 小的",
    "large": "adj. 大的",
    "next": "adj. 下一个的",
    "early": "adj. 早的",
    "young": "adj. 年轻的",
    "important": "adj. 重要的",
    "few": "adj. 很少的",
    "public": "adj. 公共的",
    "bad": "adj. 坏的",
    "same": "adj. 相同的",
    "able": "adj. 能够的",
    "so": "adv. 如此/所以",
    "up": "adv. 向上",
    "out": "adv. 出去",
    "just": "adv. 仅仅/刚才",
    "now": "adv. 现在",
    "how": "adv. 如何",
    "then": "adv. 然后",
    "more": "adv. 更多",
    "also": "adv. 也",
    "here": "adv. 这里",
    "well": "adv. 好",
    "only": "adv. 仅仅",
    "very": "adv. 非常",
    "when": "adv. 何时",
    "much": "adv. 很",
    "there": "adv. 那里",
    "even": "adv. 甚至",
    "back": "adv. 向后",
    "still": "adv. 仍然",
    "as": "adv. 同样地",
}

# ============================================
# CSS样式（手机适配）
# ============================================
def get_css():
    return f"""
    <style>
    /* 基础样式 */
    .stApp {{
        background: linear-gradient(135deg, {COLORS['bg']} 0%, {COLORS['white']} 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", sans-serif;
        padding: 5px !important;
    }}
    
    /* 标题卡片 */
    .header-card {{
        background: {COLORS['header']};
        border-radius: 12px;
        padding: 12px 15px;
        text-align: center;
        margin-bottom: 10px;
        border: 2px solid {COLORS['green']};
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    .header-card h1 {{
        color: {COLORS['green']};
        font-size: 1.4rem;
        margin: 0;
        font-weight: bold;
    }}
    .header-card p {{
        margin: 5px 0 0 0;
        font-size: 0.8rem;
        color: {COLORS['text']};
    }}
    
    /* 紧凑卡片 */
    .compact-card {{
        background: {COLORS['card']};
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
        border: 1px solid {COLORS['border']};
    }}
    
    /* 单词提示 */
    .word-tooltip {{
        position: relative;
        display: inline-block;
        cursor: help;
        border-bottom: 1px dotted {COLORS['green']};
        transition: all 0.3s;
    }}
    .word-tooltip:hover {{
        background-color: {COLORS['tooltip']};
        border-radius: 3px;
    }}
    .word-tooltip .tooltip-text {{
        visibility: hidden;
        width: 180px;
        background-color: {COLORS['text']};
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 6px 8px;
        position: absolute;
        z-index: 1000;
        bottom: 125%;
        left: 50%;
        margin-left: -90px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.85rem;
        line-height: 1.3;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }}
    .word-tooltip:hover .tooltip-text {{
        visibility: visible;
        opacity: 1;
        transition-delay: 1.5s;
    }}
    
    /* 文本显示区 */
    .text-display {{
        background: {COLORS['white']};
        border-radius: 8px;
        padding: 12px;
        font-size: 1rem;
        line-height: 1.7;
        color: {COLORS['text']};
        border: 1px solid {COLORS['border']};
        min-height: 100px;
        margin: 5px 0;
        white-space: pre-wrap;
    }}
    
    /* 高亮 */
    .highlight {{
        background-color: #FFF3CD;
        padding: 1px 4px;
        border-radius: 3px;
        font-weight: bold;
        border-bottom: 2px solid {COLORS['warn']};
    }}
    
    /* 按钮样式（手机适配） */
    .stButton > button {{
        width: 100%;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 600;
        padding: 8px 12px;
        margin: 3px 0;
        min-height: 40px;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .stButton > button:hover {{
        opacity: 0.9;
    }}
    
    /* 选择框样式 */
    .stSelectbox > div > div {{
        min-height: 40px !important;
        border-radius: 8px;
    }}
    .stSelectbox label {{
        font-size: 0.9rem !important;
        margin-bottom: 4px !important;
        font-weight: 600;
    }}
    
    /* 分区标题 */
    .section-title {{
        background: linear-gradient(90deg, {COLORS['green']}, {COLORS['success']});
        color: white;
        padding: 8px 15px;
        border-radius: 8px;
        font-size: 1rem;
        font-weight: bold;
        margin: 10px 0 8px 0;
        display: flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    
    /* 评价等级 */
    .level-excellent {{
        background-color: {COLORS['success']};
        color: white;
        padding: 8px 15px;
        border-radius: 8px;
        font-size: 1.1rem;
        font-weight: bold;
        text-align: center;
        margin: 5px 0;
    }}
    .level-warning {{
        background-color: {COLORS['warn']};
        color: white;
        padding: 8px 15px;
        border-radius: 8px;
        font-size: 1.1rem;
        font-weight: bold;
        text-align: center;
        margin: 5px 0;
    }}
    .level-error {{
        background-color: #E74C3C;
        color: white;
        padding: 8px 15px;
        border-radius: 8px;
        font-size: 1.1rem;
        font-weight: bold;
        text-align: center;
        margin: 5px 0;
    }}
    
    /* 计时器 */
    .timer-box {{
        position: fixed;
        top: 5px;
        right: 5px;
        background: {COLORS['green']};
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
        z-index: 100;
        font-size: 0.75rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    
    /* 锁屏界面 */
    .lock-screen {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, {COLORS['green']} 0%, #6B9E6B 100%);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: white;
        text-align: center;
        padding: 20px;
    }}
    .lock-screen h2 {{
        font-size: 1.8rem;
        margin-bottom: 15px;
    }}
    .countdown {{
        font-size: 3rem;
        color: #FFEB3B;
        font-weight: bold;
        margin: 15px 0;
        font-family: monospace;
    }}
    
    /* 进度条 */
    .custom-progress-container {{
        background-color: #E0E0E0;
        border-radius: 10px;
        height: 20px;
        margin: 10px 0;
        overflow: hidden;
        border: 1px solid {COLORS['border']};
    }}
    .custom-progress-fill {{
        background: linear-gradient(90deg, {COLORS['green']}, {COLORS['success']});
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 0.8rem;
        font-weight: bold;
    }}
    
    /* 手机适配 */
    @media (max-width: 768px) {{
        .header-card h1 {{
            font-size: 1.2rem;
        }}
        .text-display {{
            font-size: 0.95rem;
            padding: 10px;
        }}
        .stButton > button {{
            font-size: 0.85rem;
            padding: 6px 8px;
            min-height: 36px;
        }}
        .countdown {{
            font-size: 2.5rem;
        }}
    }}
    
    /* 隐藏Streamlit默认元素 */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* 音频控件样式 */
    audio {{
        width: 100%;
        height: 40px;
        border-radius: 8px;
        margin: 5px 0;
    }}
    
    /* 当前句子高亮 */
    .current-sentence {{
        background:#FFF3CD;
        padding:8px 12px;
        border-radius:6px;
        margin-bottom:8px;
        font-size:1rem;
        border-left:4px solid {COLORS['warn']};
    }}
    </style>
    """

st.markdown(get_css(), unsafe_allow_html=True)

# ============================================
# 核心功能：语音生成（内存流，无文件存储）
# ============================================
async def generate_speech_async(text: str, lang: str, voice: str, speed: str) -> Optional[bytes]:
    """
    异步生成语音，返回音频字节数据
    适配云端部署，无本地文件依赖
    """
    try:
        # 语音映射
        voice_map = {
            ("zh", "female"): "zh-CN-XiaoxiaoNeural",
            ("zh", "male"): "zh-CN-YunxiNeural",
            ("en", "female"): "en-US-AriaNeural",
            ("en", "male"): "en-US-GuyNeural"
        }
        selected_voice = voice_map.get((lang, voice), "zh-CN-XiaoxiaoNeural")
        
        # 生成语音
        comm = edge_tts.Communicate(text.strip(), selected_voice, rate=speed)
        audio_data = b""
        
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        return audio_data if audio_data else None
    except Exception as e:
        st.error(f"语音生成失败：{str(e)}")
        return None

def generate_and_play_speech(text: str, lang: str, voice: str, speed: str):
    """
    生成语音并直接播放（内存流）
    核心修复：避免文件存储，适配云端部署
    """
    if not text.strip():
        st.warning("⚠️ 没有可朗读的内容")
        return False
    
    # 设置加载状态
    st.session_state.loading_audio = True
    
    try:
        # 处理异步事件循环（适配Streamlit）
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 生成语音数据
        audio_data = loop.run_until_complete(generate_speech_async(text, lang, voice, speed))
        
        if audio_data:
            # 直接从内存字节流播放
            audio_bytes = BytesIO(audio_data)
            st.audio(audio_bytes, format='audio/mp3', autoplay=True)
            st.session_state.audio_playing = True
            return True
        else:
            st.error("❌ 未能生成语音数据")
            return False
    except Exception as e:
        st.error(f"播放语音失败：{str(e)}")
        return False
    finally:
        # 重置加载状态
        st.session_state.loading_audio = False

# ============================================
# 辅助功能函数
# ============================================
def auto_annotate(text, lang="zh"):
    """自动标注词语注释"""
    annotations = {}
    if lang == "zh":
        dict_to_use = BUILTIN_DICT_ZH
        for word in sorted(dict_to_use.keys(), key=len, reverse=True):
            if word in text and len(word) > 1:
                annotations[word] = dict_to_use[word]
        for char in text:
            if char in dict_to_use and char not in annotations:
                if char in "之其而以于者所乃且因":
                    annotations[char] = dict_to_use[char]
    else:
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        for word in words:
            if word in BUILTIN_DICT_EN:
                original = re.search(r'\b' + word + r'\b', text, re.IGNORECASE)
                if original:
                    annotations[original.group()] = BUILTIN_DICT_EN[word]
    return annotations

def check_eye_protection():
    """护眼提醒功能"""
    current_time = time.time()
    elapsed = current_time - st.session_state.start_time
    
    # 20分钟后锁屏
    if elapsed > 1200 and not st.session_state.is_locked:
        st.session_state.is_locked = True
        st.session_state.lock_start_time = current_time
        return True
    
    # 5分钟后解锁
    if st.session_state.is_locked and st.session_state.lock_start_time:
        rest_time = current_time - st.session_state.lock_start_time
        if rest_time > 300:
            st.session_state.is_locked = False
            st.session_state.lock_start_time = None
            st.session_state.start_time = current_time
            st.session_state.just_unlocked = True
            return False
    
    return st.session_state.is_locked

def split_sentences(text, lang="zh"):
    """分句处理"""
    if not text:
        return []
    
    if lang == "zh":
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in "。！？；\n":
                if current.strip():
                    sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())
        return sentences if sentences else [text]
    else:
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        return [s + "." for s in sentences] if sentences else [text]

def generate_annotated_text(text, annotations):
    """生成带注释的文本HTML"""
    if not annotations:
        return text
    
    sorted_words = sorted(annotations.keys(), key=len, reverse=True)
    result = text
    
    for word in sorted_words:
        if word in result and len(word) > 0:
            annotation = annotations[word]
            tooltip_html = f'<span class="word-tooltip">{word}<span class="tooltip-text">{annotation}</span></span>'
            result = result.replace(word, tooltip_html)
    
    return result

def evaluate_pronunciation(duration, standard_text, lang="zh"):
    """智能评价跟读效果"""
    if not standard_text:
        return "❌ 需要加油哦"
    
    # 计算标准时长
    if lang == "zh":
        text_length = len(standard_text.replace('\n', '').replace(' ', ''))
        standard_duration = text_length * 0.3
        min_ok, max_ok = text_length * 0.15, text_length * 0.6
    else:
        words = len(standard_text.split())
        standard_duration = words * 0.4
        min_ok, max_ok = words * 0.2, words * 0.8
    
    # 计算偏差率
    diff_ratio = abs(duration - standard_duration) / standard_duration if standard_duration > 0 else 1
    
    # 评价等级
    if diff_ratio < 0.25 and min_ok <= duration <= max_ok:
        return "✅ 优秀"
    elif diff_ratio < 0.5 and min_ok * 0.8 <= duration <= max_ok * 1.2:
        return "⚠️ 需努力"
    else:
        return "❌ 需要加油哦"

# ============================================
# 界面渲染函数
# ============================================
def render_lock_screen():
    """渲染护眼锁屏界面"""
    if st.session_state.lock_start_time:
        remaining = max(0, 300 - (time.time() - st.session_state.lock_start_time))
        minutes, seconds = int(remaining // 60), int(remaining % 60)
        
        st.markdown(f"""
        <div class="lock-screen">
            <h2>🌿 健康护眼提醒</h2>
            <p style="font-size:1rem;">已连续学习20分钟</p>
            <div class="countdown">{minutes:02d}:{seconds:02d}</div>
            <p style="font-size:0.9rem;">👀 远眺20英尺外绿色植物</p>
            <p style="font-size:0.8rem; margin-top:20px;">休息5分钟后自动解锁</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 避免频繁刷新
        time.sleep(1)
        st.rerun()

def render_welcome_back():
    """欢迎回来提示"""
    st.markdown(f"""
    <div style="position:fixed; top:0; left:0; width:100%; height:100%; 
                background:linear-gradient(135deg, {COLORS['green']} 0%, #8FBC8F 100%);
                z-index:9998; display:flex; flex-direction:column;
                justify-content:center; align-items:center;
                animation:fadeOut 2.5s forwards;">
        <h1 style="font-size:2rem; color:white;">🎉 欢迎回来！</h1>
        <p style="font-size:1rem; color:white; margin-top:10px;">继续你的朗读学习吧</p>
    </div>
    <style>
        @keyframes fadeOut {{
            0% {{ opacity: 1; }}
            85% {{ opacity: 1; }}
            100% {{ opacity: 0; visibility: hidden; }}
        }}
    </style>
    """, unsafe_allow_html=True)
    
    time.sleep(2.5)
    st.session_state.just_unlocked = False
    st.rerun()

# ============================================
# 主程序
# ============================================
def main():
    # 护眼锁屏检查
    if check_eye_protection():
        render_lock_screen()
        return
    
    # 解锁欢迎提示
    if st.session_state.get('just_unlocked', False):
        render_welcome_back()
        return

    # 计时器显示
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = max(0, 1200 - elapsed)
    mins, secs = remaining // 60, remaining % 60
    st.markdown(f'<div class="timer-box">⏱️ {elapsed//60}分 | 休息:{mins}:{secs:02d}</div>', unsafe_allow_html=True)

    # 标题区域
    st.markdown(f"""
    <div class="header-card">
        <h1>AI双语朗读老师</h1>
        <p>
            <span style="margin:0 4px;">🇨🇳中英双语</span>
            <span style="margin:0 4px;">🎯分句跟读</span>
            <span style="margin:0 4px;">📊智能评价</span>
            <span style="margin:0 4px;">💡选中注释</span>
            <span style="margin:0 4px;">🌿健康护眼</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 控制面板（手机适配的两列布局）
    col1, col2 = st.columns([1.1, 1])
    
    with col1:
        # 语言选择
        lang_opt = st.selectbox(
            "🌐 选择语言", 
            ["🇨🇳 中文", "🇬🇧 英语"],
            index=0 if st.session_state.current_lang == "zh" else 1, 
            key=f"lang_select_{st.session_state.user_id}"
        )
        
        # 切换语言逻辑
        new_lang = "zh" if lang_opt == "🇨🇳 中文" else "en"
        if new_lang != st.session_state.current_lang:
            st.session_state.current_lang = new_lang
            
            # 切换默认课文
            if new_lang == "zh":
                default_lesson = "语文示例-沁园春·雪（九年级上册）"
                st.session_state.current_lesson = default_lesson
                st.session_state.display_text = EXAMPLE_LIBRARY_ZH[default_lesson]["content"]
                st.session_state.current_annotations = EXAMPLE_LIBRARY_ZH[default_lesson]["annotations"]
            else:
                default_lesson = "英语示例（九年级）"
                st.session_state.current_lesson = default_lesson
                st.session_state.display_text = EXAMPLE_LIBRARY_EN[default_lesson]["content"]
                st.session_state.current_annotations = EXAMPLE_LIBRARY_EN[default_lesson]["annotations"]
            
            st.session_state.current_sentence = 0
            st.session_state.text_area_key += 1
            st.rerun()

        # 示例课文选择
        st.markdown(f'<span style="font-weight:bold; color:{COLORS["green"]}; font-size:0.9rem; margin-bottom:5px; display:block;">📚 选择示例课文</span>', unsafe_allow_html=True)
        st.markdown('<div class="compact-card">', unsafe_allow_html=True)
        
        with st.expander("📋 点击展开选择课文", expanded=False):
            # 根据当前语言显示对应示例
            if st.session_state.current_lang == "zh":
                example_options = list(EXAMPLE_LIBRARY_ZH.keys())
            else:
                example_options = list(EXAMPLE_LIBRARY_EN.keys())
            
            # 确保当前课文在选项中
            if st.session_state.current_lesson not in example_options:
                st.session_state.current_lesson = example_options[0]
            
            # 课文选择框
            selected_example = st.selectbox(
                "示例课文", 
                example_options,
                index=example_options.index(st.session_state.current_lesson) if st.session_state.current_lesson in example_options else 0,
                label_visibility="collapsed", 
                key=f"example_select_{st.session_state.user_id}"
            )
            
            # 加载示例课文按钮
            if st.button("🔄 加载选中课文", use_container_width=True, key=f"load_example_{st.session_state.user_id}"):
                st.session_state.current_lesson = selected_example
                
                # 加载对应课文内容
                if st.session_state.current_lang == "zh":
                    data = EXAMPLE_LIBRARY_ZH[selected_example]
                else:
                    data = EXAMPLE_LIBRARY_EN[selected_example]
                
                st.session_state.display_text = data["content"]
                st.session_state.current_annotations = data["annotations"]
                st.session_state.current_sentence = 0
                st.session_state.text_area_key += 1
                
                st.success(f"✅ 已加载：{selected_example}")
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        # 声音选择
        voice_opt = st.selectbox(
            "🎙️ 选择声音", 
            ["👩 女声", "👨 男声"],
            index=0 if st.session_state.current_voice == "female" else 1, 
            key=f"voice_select_{st.session_state.user_id}"
        )
        st.session_state.current_voice = "female" if voice_opt == "👩 女声" else "male"
        
        # 语速选择
        speed_opt = st.selectbox(
            "⚡ 选择语速", 
            ["🐢 慢速", "🐇 正常", "🚀 快速"], 
            key=f"speed_select_{st.session_state.user_id}"
        )
        speed_map = {"🐢 慢速": "-20%", "🐇 正常": "+0%", "🚀 快速": "+20%"}
        selected_speed = speed_map[speed_opt]

    # 课文编辑区域
    st.markdown("---")
    text_key = f"text_edit_{st.session_state.text_area_key}_{st.session_state.user_id}"
    
    # 课文内容编辑框
    new_text = st.text_area(
        "✏️ 课文内容（可直接编辑修改）", 
        value=st.session_state.display_text, 
        height=120, 
        key=text_key
    )
    
    # 文本变化时自动标注
    if new_text != st.session_state.display_text:
        st.session_state.display_text = new_text
        st.session_state.current_annotations = auto_annotate(new_text, st.session_state.current_lang)
        st.session_state.current_sentence = 0

    # 分句处理
    sentences = split_sentences(st.session_state.display_text, st.session_state.current_lang)
    
    # 当前句子显示
    if sentences and st.session_state.current_sentence < len(sentences):
        curr_sent = sentences[st.session_state.current_sentence]
        st.markdown(f"""
        <div class="current-sentence">
             当前句子：{curr_sent}
        </div>
        """, unsafe_allow_html=True)

    # 带注释的文本显示
    annotated_text = generate_annotated_text(st.session_state.display_text, st.session_state.current_annotations)
    st.markdown(f'<div class="text-display">{annotated_text}</div>', unsafe_allow_html=True)
    st.caption("💡 提示：长按/悬停词语1.5秒查看注释 | 支持手机触屏操作")

    # 进度条显示
    if sentences:
        progress = (st.session_state.current_sentence + 1) / len(sentences)
        progress_percent = int(progress * 100)
        current_num = st.session_state.current_sentence + 1
        total_num = len(sentences)
        
        st.markdown(f"""
        <div style="margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 0.9rem; color: {COLORS['text']};">
                <span>📊 朗读进度</span>
                <span>第 {current_num} / {total_num} 句 ({progress_percent}%)</span>
            </div>
            <div class="custom-progress-container">
                <div class="custom-progress-fill" style="width: {progress_percent}%;">
                    {progress_percent}%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 朗读控制按钮
    st.markdown("---")
    st.markdown('<div class="section-title">🎤 朗读控制</div>', unsafe_allow_html=True)
    
    # 分句朗读按钮组
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    
    with btn_col1:
        if st.button("⬅️ 上一句", use_container_width=True, key=f"prev_sent_{st.session_state.user_id}"):
            if st.session_state.current_sentence > 0:
                st.session_state.current_sentence -= 1
                # 播放上一句
                if sentences and st.session_state.current_sentence < len(sentences):
                    sent = sentences[st.session_state.current_sentence]
                    generate_and_play_speech(
                        sent,
                        st.session_state.current_lang,
                        st.session_state.current_voice,
                        selected_speed
                    )
                st.rerun()
            else:
                st.warning("⚠️ 已是第一句")
    
    with btn_col2:
        # 加载状态显示
        if st.session_state.loading_audio:
            st.button("⏳ 生成语音中...", disabled=True, use_container_width=True)
        else:
            if st.button("▶️ 朗读本句", use_container_width=True, type="primary", key=f"play_curr_{st.session_state.user_id}"):
                if sentences and st.session_state.current_sentence < len(sentences):
                    sent = sentences[st.session_state.current_sentence]
                    generate_and_play_speech(
                        sent,
                        st.session_state.current_lang,
                        st.session_state.current_voice,
                        selected_speed
                    )
                else:
                    st.warning("⚠️ 没有可朗读的内容")
    
    with btn_col3:
        if st.button("➡️ 下一句", use_container_width=True, key=f"next_sent_{st.session_state.user_id}"):
            if st.session_state.current_sentence < len(sentences) - 1:
                st.session_state.current_sentence += 1
                # 播放下一句
                if sentences and st.session_state.current_sentence < len(sentences):
                    sent = sentences[st.session_state.current_sentence]
                    generate_and_play_speech(
                        sent,
                        st.session_state.current_lang,
                        st.session_state.current_voice,
                        selected_speed
                    )
                st.rerun()
            else:
                st.warning("⚠️ 已是最后一句")
    
    # 全文朗读按钮
    if st.button("📖 全文朗读", use_container_width=True, key=f"play_all_{st.session_state.user_id}"):
        if st.session_state.display_text.strip():
            generate_and_play_speech(
                st.session_state.display_text,
                st.session_state.current_lang,
                st.session_state.current_voice,
                selected_speed
            )
        else:
            st.warning("⚠️ 课文内容为空")

    # 跟读练习区域
    st.markdown("---")
    st.markdown('<div class="section-title">🎧 跟读练习</div>', unsafe_allow_html=True)
    
    rec_cols = st.columns([1, 1, 2])
    
    with rec_cols[0]:
        if not st.session_state.get('recording'):
            if st.button("🎙️ 开始录音", use_container_width=True, type="primary", key=f"start_rec_{st.session_state.user_id}"):
                st.session_state.recording = True
                st.session_state.record_start = time.time()
                st.session_state.record_level = ""
                st.rerun()
        else:
            st.button("⏺️ 录音中...", disabled=True, use_container_width=True)
    
    with rec_cols[1]:
        if st.session_state.get('recording'):
            if st.button("🛑 停止录音", use_container_width=True, key=f"stop_rec_{st.session_state.user_id}"):
                duration = time.time() - st.session_state.record_start
                st.session_state.recording = False
                st.session_state.recording_duration = duration
                
                # 评价跟读效果
                curr_text = sentences[st.session_state.current_sentence] if sentences else ""
                level = evaluate_pronunciation(duration, curr_text, st.session_state.current_lang)
                st.session_state.record_level = level
                st.rerun()
        else:
            st.button("🛑 停止录音", disabled=True, use_container_width=True)
    
    with rec_cols[2]:
        if st.session_state.get('recording'):
            dur = time.time() - st.session_state.record_start
            st.markdown(f"**⏱️ 录音时长: {dur:.1f}秒**")
        elif st.session_state.get('record_level'):
            level = st.session_state.record_level
            if "优秀" in level:
                st.markdown(f'<div class="level-excellent">{level}</div>', unsafe_allow_html=True)
            elif "需努力" in level:
                st.markdown(f'<div class="level-warning">{level}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="level-error">{level}</div>', unsafe_allow_html=True)
        else:
            st.caption("点击开始录音，跟读当前句子")

    # 底部说明
    st.markdown("---")
    st.caption("📱 适配手机访问 | 🇨🇳中英双语 | 🎯分句跟读 | 📊智能评价 | 🌿健康护眼")
    
    # 录音状态自动刷新（降低频率，适配云端）
    if st.session_state.get('recording'):
        time.sleep(0.8)
        st.rerun()

# ============================================
# 程序入口
# ============================================
if __name__ == "__main__":
    main()
