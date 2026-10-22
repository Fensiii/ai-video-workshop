"""美德·自由 文案总表 → 生成 stories/freedom.js。改文案只改这里，然后重新运行本脚本。
卡片的出场时间/位置/角度沿用七美德系列的编排（LAYOUT）；画面上不出现“七美德”字样。
figure 指定人物文件 figures/<figure>.js（自由 = 被锁链捆住、火炬熄灭的自由女神像 → 举起火炬的金色女神）；
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
# 卡片：(谁说的, 标题=别人的安排 / 对自己说的话, 副标题=真相)。画面撕裂的瞬间，卡片会闪出副标题里的真相。
V['freedom'] = dict(
    no=4, cn='自由', figure='liberty', truth_flip=True, transition='slash', latin='LIBERTAS · FREEDOM',
    question=['人生早被安排好了，为什么偏要', '自己选', '？'],
    tag='美德 · 心无枷锁', ring='LIBERTAS INAESTIMABILIS RES EST · LIBERTAS · ',
    fig=dict(accent='#fff4dc', glow='#ffb040'), key=-2,
    cards=[('妈妈', '考个编制，稳定最重要', '你根本不想去'), ('亲戚', '女孩子别跑那么远', '那是你的梦想'),
           ('老板', '这周末辛苦加个班', '连续第 9 个周末'), ('群聊', '大家都是这么过来的', '所以你也只能这样？'),
           ('自己', '等存够钱再辞职', '已经等了 6 年'), ('相亲', '条件合适就行，感情慢慢培养', '你不爱他'),
           ('朋友圈', '别人会怎么看你', '其实没人在看你'), ('爸爸', '画画能当饭吃吗', '你画了 15 年'),
           ('同事', '枪打出头鸟', '你又把话咽回去了'), ('自己', '再忍忍就好了', '已经忍了 2000 天'),
           ('房贷', '本月应还 8,600 元', '还剩 287 期'), ('导师', '照我说的写就行', '那不是你想研究的'),
           ('邻居', '30 岁还不结婚？', '这是你的人生'), ('自己', '我不行的', '你从来没试过'),
           ('打卡', '今日已打卡 08:59', '第 1,860 天'), ('家族群', '听话的孩子才有出息', '你活成了他们'),
           ('简历', '已投递：最稳的那家', '心里想的是另一家'), ('自己', '以后再说吧', '以后是什么时候？')],
    words=['应该', '听话', '别折腾', '稳定', '按部就班', '忍着', '别人都这样', '不敢', '怕失败', '面子',
           '规矩', '认命', '将就', '算了', '随大流', '服从', '安分', '不配', '等以后', '别做梦',
           '乖一点', '不许', '必须', '照做', '忍忍就过去了'],
    chars=['囚', '困', '锁', '缚', '怕', '忍', '笼', '枷', '从', '惧'],
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
