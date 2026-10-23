"""美德·忠诚 文案总表 → 生成 stories/loyalty.js。改文案只改这里，然后重新运行本脚本。
卡片的出场时间/位置/角度沿用七美德系列的编排（LAYOUT）；画面上不出现“七美德”字样。
figure 指定人物文件 figures/<figure>.js（忠诚 = 伸手去够银币袋的骑士 → 持剑宣誓的金甲骑士）；
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
# 卡片：(谁发来的, 标题=诱惑 / 对自己说的话, 副标题=真相)。画面撕裂的瞬间，卡片会闪出副标题里的真相。
V['loyalty'] = dict(
    no=6, cn='忠诚', figure='knight', truth_flip=True, transition='slash', latin='FIDELITAS · LOYALTY',
    question=['明明背叛更划算，为什么偏要', '守着', '？'],
    tag='美德 · 至死不渝', ring='SEMPER FIDELIS · FIDELITAS · ',
    fig=dict(accent='#fff4dc', glow='#ffb040'), key=1,
    cards=[('猎头', '对方开价翻倍，今晚就签', '项目还有三天上线'), ('前任', '在吗？出来喝一杯', '她在家等你吃饭'),
           ('群聊', '大家都在骂他，你也说两句', '他是你最好的兄弟'), ('竞对', '把客户名单带过来就行', '那是你老东家的'),
           ('自己', '他不会知道的', '你自己知道'), ('老板', '把锅甩给新人吧', '他替你熬了三个通宵'),
           ('匿名', '把他的聊天记录发我，给你五千', '他把你当自己人'), ('交友软件', '附近有 99+ 人想认识你', '婚戒还戴在手上'),
           ('转账', '收到 ¥30,000：封口费', '三十枚银币'), ('团队', '这功劳你一个人领了吧', '是大家一起熬出来的'),
           ('兄弟', '我出事了，能帮我一下吗', '你回了句“在忙”'), ('合伙人', '撤资吧，趁现在还来得及', '你们说好一起扛'),
           ('自己', '谁不是为自己活', '那你还剩下谁'), ('猎头', '把原团队一起带走', '他们那么信你'),
           ('爸妈', '今年过年回来吗', '第三年没回了'), ('自己', '良心又不能当饭吃', '能'),
           ('对家', '换个阵营，待遇更好', '你发过誓的'), ('承诺', '我会一直在', '说过的话还算数吗')],
    words=['背叛', '跳槽', '出卖', '两面三刀', '墙头草', '见利忘义', '反水', '食言', '变心', '甩锅',
           '钱更重要', '谁给得多', '不值得', '先顾自己', '翻脸', '算计', '一走了之', '临阵脱逃', '卖队友', '口是心非',
           '人走茶凉', '各为其主', '没人知道', '就这一次', '背后捅刀'],
    chars=['叛', '贪', '诈', '逃', '背', '欺', '私', '诡', '弃', '变'],
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
