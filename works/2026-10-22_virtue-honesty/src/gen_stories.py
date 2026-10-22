"""美德·诚实 文案总表 → 生成 stories/honesty.js。改文案只改这里，然后重新运行本脚本。
卡片的出场时间/位置/角度沿用七美德系列的编排（LAYOUT）；画面上不出现“七美德”字样。
figure 指定人物文件 figures/<figure>.js（诚实 = 提线木偶 → 真正的少年）。"""
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
# 卡片：(应用, 标题=说出口的话, 副标题=真相)。画面撕裂的瞬间，卡片会闪出副标题里的真相。
V['honesty'] = dict(
    no=8, cn='诚实', figure='puppet', truth_flip=True, latin='HONESTAS · HONESTY', question=['明明可以骗过去，为什么还要', '说真话', '？'],
    tag='美德 · 以诚待人', ring='VERITAS LIBERABIT VOS · HONESTAS · ',
    fig=dict(accent='#d8f4ff', glow='#7fd4ff'), key=2,
    cards=[('微信', '在路上了，马上到', '（其实刚起床）'), ('朋友圈', '随手一拍，原图直出', '精修 2 小时，滤镜 ×3'),
           ('简历', '精通 Excel、Python', '只会 Ctrl+C / Ctrl+V'), ('私信', '刚看到消息', '已读 3 小时'),
           ('直播间', '全网最低价！', '原价今天刚改的'), ('家长群', '孩子考了全班第五', '倒数的'),
           ('工作群', '收到，正在推进', '文件还没打开'), ('电话', '信号不好，先挂了', '信号满格'),
           ('私信', '我没事，真的', '哭了一整晚'), ('同事', '这锅不是我的', '是我忘了提交'),
           ('外卖', '商家已出餐', '骑手还没接单'), ('直播间', '最后 3 单！', '库存 9999'),
           ('私信', '这个我早就知道', '刚刚才搜的'), ('评论区', '亲测有效！', '收了 200 块'),
           ('家族群', '工作挺好的，不累', '连续加班 21 天'), ('私信', '就这一次，别告诉别人', '没人会知道的'),
           ('账单', '这个月没怎么花', '花呗已逾期'), ('老师', '作业被狗吃了', '家里没有狗')],
    words=['在路上了', '刚看到', '我没事', '信号不好', '没人知道', '编个理由', '先瞒着', '演一下', '不是我', '都是误会',
           '改下数据', 'P 一下', '善意的谎言', '装作很好', '别承认', '删记录', '圆回来', '最后一次', '全网最低', '亲测有效',
           '假装很忙', '随口一说', '我发誓', '真的真的', '面子要紧'],
    chars=['谎', '骗', '假', '瞒', '伪', '装', '演', '编', '诈', '掩'],
)

os.makedirs('stories', exist_ok=True)
for vid, v in V.items():
    cards = []
    for i, ((app, title, body), lay) in enumerate(zip(v['cards'], LAYOUT)):
        cards.append(lay + [app, app[0], ICON_COLORS[(i * 3 + v['no']) % len(ICON_COLORS)], title, body])
    story = dict(duration=25.2, no=v['no'], figure=v['figure'], truthFlip=v['truth_flip'], tag=v['tag'], question=v['question'], title=v['cn'], latin=v['latin'],
                 ring=v['ring'], fig=v['fig'], key=v['key'], cards=cards, words=v['words'], chars=v['chars'])
    js = 'window.STORY = ' + json.dumps(story, ensure_ascii=False, indent=1) + ';\n'
    # 时间轴（与七美德系列一致，另加画面劈开）；audio.py 按 “t: {...}” 读取
    js += """window.STORY.t = {
  figure: 4.6, grey: 8.9, slash: 9.05, split: 9.18, flash: 9.45, gold: 9.55,
  tag: 11.9, question: 12.2, title: 12.9, latin: 13.6, fadeOut: 24.1,
};
"""
    open(f'stories/{vid}.js', 'w', encoding='utf-8').write(js)
    print(vid, len(cards))
