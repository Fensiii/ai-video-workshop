"""美德·自律 文案总表 → 生成 stories/discipline.js。改文案只改这里，然后重新运行本脚本。
卡片的出场时间/位置/角度沿用七美德系列的编排（LAYOUT）；画面上不出现“七美德”字样。
figure 指定人物文件 figures/<figure>.js（自律 = 沙发上的胖子 → 雕像般的肌肉男）；
transition='shatter' 时转场用玻璃破碎（默认 'slash' 金光斜斩劈开）。"""
import json, os

LAYOUT = [  # [出现时刻, x, y, 旋转°, 缩放]
    [0.55, 250, 360, -4, 1.00], [1.25, 620, 250, 3, 0.95], [1.85, 300, 620, 2, 1.00], [2.40, 1450, 300, -6, 0.92],
    [2.85, 700, 760, -3, 0.98], [3.25, 1380, 640, 8, 0.90], [3.60, 160, 160, 5, 0.85], [3.90, 980, 150, -8, 0.88],
    [4.20, 1600, 820, -5, 0.86], [4.45, 520, 470, -10, 0.84], [4.70, 60, 860, 7, 0.82], [4.95, 1100, 900, 12, 0.80],
    [5.20, 860, 470, -14, 0.78], [5.45, 120, 470, 15, 0.80], [5.70, 1500, 120, 10, 0.78], [5.95, 620, 950, -18, 0.76],
    [6.20, 1200, 40, -12, 0.74], [6.40, 380, 60, 18, 0.72],
]
ICON_COLORS = ['#3f6f8f', '#b8452f', '#c9822b', '#6c4a8f', '#2f7a66', '#b03a5b', '#4d6aa8', '#c46f8c', '#6b6b6b', '#7a6a3a']

V = {}
# 卡片：(应用, 标题=对自己说的话 / 推送, 副标题=真相)。画面撕裂的瞬间，卡片会闪出副标题里的真相。
V['discipline'] = dict(
    no=9, cn='自律', figure='athlete', truth_flip=True, transition='shatter', latin='DISCIPLINA · DISCIPLINE',
    question=['明明可以明天再开始，为什么偏要', '今天', '？'],
    tag='美德 · 自律即自由', ring='FORTISSIMUS EST QUI SE VINCIT · DISCIPLINA · ',
    fig=dict(accent='#fff4dc', glow='#ffb040'), key=5,
    cards=[('闹钟', '再睡 5 分钟', '已经按掉第 6 次'), ('备忘录', '明天开始减肥', '第 47 个明天'),
           ('外卖', '炸鸡已送达，趁热吃', '本周第 9 单'), ('视频', '再看一集就睡', '现在凌晨 3:40'),
           ('健身房', '你已 32 天未打卡', '年卡 3999 元'), ('奶茶', '全糖去冰，第二杯半价', '今天第 3 杯'),
           ('短视频', '刷 10 分钟就学习', '已刷 3 小时'), ('体重秤', '一定是秤坏了', '+18.6 kg'),
           ('自己', '今天太累了，歇一天', '已经歇了半年'), ('购物车', '买了跑鞋就去跑', '吊牌还没拆'),
           ('游戏', '最后一把！', '第 12 个最后一把'), ('计划表', '下周一正式开始', '去年就这么说'),
           ('沙发', '躺一下就起来', '躺了一下午'), ('宵夜', '吃饱了才有力气减肥', '凌晨 1 点的烧烤'),
           ('收藏夹', '7 天练出马甲线', '收藏了，没练'), ('亲戚', '胖点有福气', '体检：脂肪肝'),
           ('书架', '这本周末看完', '塑封都没拆'), ('闹钟', '已自动延后 30 分钟', '迟到第 3 次')],
    words=['再睡会', '明天再说', '就一集', '最后一口', '点外卖', '躺平', '不想动', '下周开始', '太累了', '奖励自己',
           '再刷会', '熬夜', '奶茶', '炸鸡', '算了吧', '没时间', '先放着', '宵夜', '拖延', '懒得练',
           '晚点再说', '差不多得了', '反正瘦不了', '吃饱再减', '今天例外'],
    chars=['懒', '拖', '馋', '躺', '惰', '怠', '贪', '散', '睡', '逸'],
)

os.makedirs('stories', exist_ok=True)
for vid, v in V.items():
    cards = []
    for i, ((app, title, body), lay) in enumerate(zip(v['cards'], LAYOUT)):
        cards.append(lay + [app, app[0], ICON_COLORS[(i * 3 + v['no']) % len(ICON_COLORS)], title, body])
    story = dict(duration=25.2, no=v['no'], figure=v['figure'], truthFlip=v['truth_flip'], transition=v.get('transition', 'slash'), tag=v['tag'], question=v['question'], title=v['cn'], latin=v['latin'],
                 ring=v['ring'], fig=v['fig'], key=v['key'], cards=cards, words=v['words'], chars=v['chars'])
    js = 'window.STORY = ' + json.dumps(story, ensure_ascii=False, indent=1) + ';\n'
    # 时间轴；audio.py 按 “t: {...}” 读取。slash：斜斩劈开（七美德系列）；shatter：玻璃破碎——
    # crack 第一击（撞击点碎成蛛网）、crack2 裂纹爬满全屏、flash 整屏炸碎（碎片慢动作漂一会儿再飞走）
    if story['transition'] == 'shatter':
        js += """window.STORY.t = {
  figure: 4.6, grey: 8.7, crack: 8.8, crack2: 9.15, flash: 9.5, gold: 9.6,
  tag: 11.9, question: 12.2, title: 12.9, latin: 13.6, fadeOut: 24.1,
};
"""
    else:
        js += """window.STORY.t = {
  figure: 4.6, grey: 8.9, slash: 9.05, split: 9.18, flash: 9.45, gold: 9.55,
  tag: 11.9, question: 12.2, title: 12.9, latin: 13.6, fadeOut: 24.1,
};
"""
    open(f'stories/{vid}.js', 'w', encoding='utf-8').write(js)
    print(vid, len(cards))
