import random
from datetime import date, timedelta

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
EVAL_DATE = date(2026, 11, 13)

REGIONS = [
    {"work": "杭州", "hometowns": ["衢州", "金华", "绍兴"], "trips": ["上海", "南京"]},
    {"work": "上海", "hometowns": ["苏州", "嘉兴", "南通"], "trips": ["北京", "杭州"]},
    {"work": "北京", "hometowns": ["天津", "石家庄", "保定"], "trips": ["上海", "济南"]},
    {"work": "深圳", "hometowns": ["广州", "惠州", "长沙"], "trips": ["上海", "武汉"]},
    {"work": "成都", "hometowns": ["绵阳", "重庆", "乐山"], "trips": ["西安", "重庆"]},
    {"work": "南京", "hometowns": ["镇江", "扬州", "滁州"], "trips": ["上海", "北京"]},
    {"work": "武汉", "hometowns": ["孝感", "黄冈", "荆州"], "trips": ["深圳", "上海"]},
    {"work": "西安", "hometowns": ["咸阳", "宝鸡", "渭南"], "trips": ["成都", "北京"]},
]
OCCUPATIONS = ["产品经理", "后端工程师", "小学语文老师", "护士", "会计", "UI设计师", "销售", "运营专员", "记者", "公务员"]
NAMES = [("李承泽", "男"), ("赵敏", "女"), ("陈嘉怡", "女"), ("刘宇航", "男"), ("杨帆", "男"),
         ("周雨桐", "女"), ("吴磊", "男"), ("郑晓峰", "男"), ("孙悦", "女"), ("马天宇", "男"),
         ("沈亦舟", "男"), ("林知夏", "女"), ("顾明轩", "男"), ("苏晚晴", "女"), ("韩景行", "男")]
ALLERGIES = [
    {"name": "花生", "detail": "严重，随身携带过敏药", "hint": "说自己花生过敏挺严重，随身都带着过敏药，让助手以后推荐食物千万避开花生"},
    {"name": "海鲜", "detail": "严重，随身携带过敏药", "hint": "说自己海鲜过敏挺严重，随身带过敏药，让助手推荐食物避开海鲜"},
    {"name": "芒果", "detail": "吃芒果会起疹子", "hint": "说自己芒果过敏，吃芒果会起疹子，让助手推荐水果避开芒果"},
    {"name": "花粉", "detail": "春天出门要戴口罩", "hint": "说自己花粉过敏，春天出门得戴口罩，让助手留意花期"},
]
HABITS = [
    {"habit": "晨跑", "place": "江边步道", "body": "膝盖", "disruption": "跑步膝", "substitute": "骑行",
     "disrupt_hint": "用主语省略说自己去医院拍了片子，医生说是跑步膝，让先别跑了",
     "sub_hint": "说游泳还没学会，就先骑车，把上次说的那个江边步道改成骑行路线"},
    {"habit": "夜跑", "place": "公园步道", "body": "脚踝", "disruption": "脚踝扭伤", "substitute": "游泳",
     "disrupt_hint": "用主语省略说自己去医院拍了片子，医生说是脚踝扭伤，让先别跑了",
     "sub_hint": "说骑行不太会，就先游泳，把上次说的那个公园步道换成泳池"},
    {"habit": "健身", "place": "体育中心", "body": "腰", "disruption": "腰肌劳损", "substitute": "散步",
     "disrupt_hint": "用主语省略说自己去医院检查了，医生说是腰肌劳损，让先别练了",
     "sub_hint": "说跑步太累，就先散步，把上次说的那个体育中心换成小区绿道"},
    {"habit": "骑行", "place": "滨江绿道", "body": "膝盖", "disruption": "膝盖积液", "substitute": "慢跑",
     "disrupt_hint": "用主语省略说自己去医院抽了积液，医生说是膝盖积液，让先别骑了",
     "sub_hint": "说游泳还没学会，就先慢跑，把上次说的那个滨江绿道改成慢跑路线"},
]
HOBBIES = [
    {"class": "吉他班", "short": "吉他", "d1": "周三晚上", "d2": "周六下午", "reason": "老师周三晚上有事"},
    {"class": "烘焙班", "short": "烘焙", "d1": "周日上午", "d2": "周日下午", "reason": "上午的教室被占用"},
    {"class": "书法班", "short": "书法", "d1": "周二晚上", "d2": "周四晚上", "reason": "老师周二晚上有事"},
    {"class": "摄影班", "short": "摄影", "d1": "周六上午", "d2": "周日上午", "reason": "周六上午要加班"},
    {"class": "尤克里里班", "short": "尤克里里", "d1": "周五晚上", "d2": "周六上午", "reason": "周五晚上场地检修"},
]
GOALS = [
    {"goal": "开放水域潜水证", "token": "潜水证", "place": "千岛湖", "prep": "理论课已经刷完了"},
    {"goal": "瑜伽教练证", "token": "瑜伽", "place": "瑜伽培训机构", "prep": "理论课已经学完了"},
    {"goal": "咖啡师证", "token": "咖啡师", "place": "咖啡培训学校", "prep": "理论课已经刷完了"},
    {"goal": "普通话二级甲等证书", "token": "普通话", "place": "普通话测试站", "prep": "练习题已经刷完了"},
    {"goal": "急救员证", "token": "急救", "place": "红十字会培训中心", "prep": "理论课已经学完了"},
]
ABSTENTION_POOL = [
    {"topic": "养猫", "words": ["猫"], "q": "{name}养猫吗？"},
    {"topic": "婚姻", "words": ["结婚", "婚姻", "老公", "老婆", "丈夫", "妻子", "已婚", "未婚", "男朋友", "女朋友"], "q": "{name}结婚了吗？"},
    {"topic": "手机号", "words": ["手机号", "电话号", "手机号码"], "q": "{name}的手机号是多少？"},
    {"topic": "星座", "words": ["星座", "白羊", "金牛", "双子", "巨蟹", "狮子", "处女", "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼"], "q": "{name}是什么星座？"},
    {"topic": "血型", "words": ["血型", "A型", "B型", "O型", "AB型"], "q": "{name}是什么血型？"},
]


def cn(d):
    return f"{d.month}月{d.day}日"


def full(d):
    return f"{d.year}年{d.month}月{d.day}日"


def monday_of(d):
    return d - timedelta(days=d.weekday())


def build_dates(rng):
    m = rng.choice([8, 9, 10])
    s1 = date(2026, m - 2, rng.randint(1, 5))
    s2 = date(2026, m - 2, rng.randint(18, 25))
    s3 = date(2026, m - 1, rng.randint(8, 15))
    s4 = date(2026, m, rng.randint(5, 10))
    s5 = date(2026, m, rng.randint(25, 29))
    return {
        "s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5,
        "completion": s5 - timedelta(days=1),
        "followup": s2 + timedelta(days=2),
        "trip_mon": monday_of(s3) + timedelta(days=14),
        "month": m, "next_month": m + 1,
    }


def build_user(index):
    rng = random.Random(index * 7919)
    off = index - 2
    name, gender = NAMES[off % len(NAMES)]
    region = REGIONS[off % len(REGIONS)]
    occupation = OCCUPATIONS[off % len(OCCUPATIONS)]
    allergy = ALLERGIES[off % len(ALLERGIES)]
    habit = HABITS[off % len(HABITS)]
    hobby = HOBBIES[off % len(HOBBIES)]
    goal = GOALS[off % len(GOALS)]
    work = region["work"]
    hometown = rng.choice(region["hometowns"])
    trip = rng.choice(region["trips"])
    age = rng.randint(24, 38)
    abstentions = rng.sample(ABSTENTION_POOL, 2)
    d = build_dates(rng)
    tm = d["trip_mon"]
    trip_sun = tm + timedelta(days=6)
    trip_end = f"{trip_sun.month}月{trip_sun.day}日" if trip_sun.month != tm.month else f"{trip_sun.day}日"
    xun = "上旬" if tm.day <= 10 else ("中旬" if tm.day <= 20 else "下旬")
    h, place, body = habit["habit"], habit["place"], habit["body"]
    habit_verbs = {"晨跑": ["晨跑", "跑步", "跑"], "夜跑": ["夜跑", "跑步", "跑"], "健身": ["健身", "练"], "骑行": ["骑行", "骑车", "骑"]}[h]
    dis, sub = habit["disruption"], habit["substitute"]
    cls, short, d1, d2, reason = hobby["class"], hobby["short"], hobby["d1"], hobby["d2"], hobby["reason"]
    g, gtok, gplace, prep = goal["goal"], goal["token"], goal["place"], goal["prep"]

    persona = {"name": name, "gender": gender, "age": age, "city": work,
               "hometown": hometown, "occupation": occupation,
               "traits": [f"{allergy['name']}过敏", "乳糖不耐", f"爱{h}", "父母在老家"]}

    def fact(fid, text, planted, status="stable", superseded_by=None, token=None):
        f = {"fact_id": fid, "text": text, "planted_in": planted, "status": status}
        if superseded_by:
            f["superseded_by"] = superseded_by
        if token:
            f["token"] = token
        return f

    facts = [
        fact("F1", f"用户名字是{name}", ["s1"], token=name),
        fact("F2", f"用户在{work}工作，是{occupation}", ["s1"], token=work),
        fact("F3", f"用户老家是{hometown}，父母住在{hometown}老城区，离火车站不远", ["s1", "s3"], token=hometown),
        fact("F4", f"用户{allergy['name']}过敏，{allergy['detail']}", ["s1"], token=allergy["name"]),
        fact("F5", f"用户坚持{h}锻炼，常去{place}", ["s1"], "superseded", "F6", habit_verbs),
        fact("F6", f"用户{cn(d['s2'])}前后{body}受伤（{dis}），医生要求暂停{h}", ["s2"], "superseded", "F16", dis),
        fact("F7", f"用户暂停{h}期间改为{sub}", ["s2"], "superseded", "F16", sub),
        fact("F8", f"用户{cn(d['s2'])}表示过两天（约{cn(d['followup'])}）去复查{body}", ["s2"], token="复查"),
        fact("F9", f"用户{cn(d['s3'])}表示下下周（{cn(tm)}至{trip_end}那一周）去{trip}出差三天", ["s3"], token=trip),
        fact("F10", f"用户{trip}出差结束后顺路回{hometown}看父母", ["s3"], token=hometown),
        fact("F11", f"用户{cn(d['s3'])}前后{body}复查通过，医生建议逐步恢复{h}", ["s3"], token="复查"),
        fact("F12", "用户乳糖不耐，喝奶茶要换燕麦奶", ["s4"], token="燕麦"),
        fact("F13", f"用户报了{cls}，每周{d1}上课，零基础", ["s4"], "superseded", "F17", short),
        fact("F14", f"用户计划{d['month']}月底去{gplace}考{g}，{prep}", ["s4"], "superseded", "F18", gtok),
        fact("F15", f"用户考{g}的事暂时瞒着父母，怕他们念叨", ["s4"], token="瞒"),
        fact("F16", f"用户{body}痊愈，{cn(d['s5'])}前后已恢复{h}锻炼，循序渐进", ["s5"], token=habit_verbs),
        fact("F17", f"用户{cls}因{reason}，从{cn(d['s5'])}前后起改为每周{d2}", ["s5"], token=d2[:2]),
        fact("F18", f"用户{full(d['completion'])}考下{g}", ["s5"], token=gtok),
        fact("F19", f"用户父母{d['next_month']}月来{work}住一阵", ["s5"], "plan", token="爸"),
    ]

    sessions = [
        {"session_id": "s1", "date": d["s1"].isoformat(), "date_cn": cn(d["s1"]), "weekday": WEEKDAYS[d["s1"].weekday()],
         "design_notes": ["首次会话自我介绍，埋稳定事实", "日期锚点"],
         "phenomena": ["第一条user消息自然带出会话日期", "自我介绍建立身份"],
         "plant": [
             {"fact_id": "F1", "hint": f"自我介绍叫{name}，做{occupation}的，让助手当日常助手"},
             {"fact_id": "F2", "hint": f"说自己在{work}上班"},
             {"fact_id": "F3", "hint": f"说老家是{hometown}的，爸妈还在那边"},
             {"fact_id": "F4", "hint": allergy["hint"]},
             {"fact_id": "F5", "hint": f"说自己平时坚持{h}，常去{place}，锻炼完精神好"},
         ], "messages": []},
        {"session_id": "s2", "date": d["s2"].isoformat(), "date_cn": cn(d["s2"]), "weekday": WEEKDAYS[d["s2"].weekday()],
         "design_notes": ["主语省略", "模糊时间：过两天", f"指代：上次说的那个{place}", f"更新链启动：{h}→暂停→{sub}"],
         "phenomena": ["第一条user消息自然带出会话日期", "主语省略：去医院/检查时不带主语我", "模糊时间：过两天去复查", f"指代：上次说的那个{place}"],
         "plant": [
             {"fact_id": "F6", "hint": habit["disrupt_hint"]},
             {"fact_id": "F7", "hint": habit["sub_hint"]},
             {"fact_id": "F8", "hint": "说约了过两天去复查，看看恢复得怎么样"},
         ], "messages": []},
        {"session_id": "s3", "date": d["s3"].isoformat(), "date_cn": cn(d["s3"]), "weekday": WEEKDAYS[d["s3"].weekday()],
         "design_notes": ["模糊时间：下下周（需周历推算）", f"指代：上次说的那个{body}", "跨会话事实强化：父母住址"],
         "phenomena": ["第一条user消息自然带出会话日期", "模糊时间：下下周去出差（不要换算成绝对日期）", f"指代：上次说的那个{body}", "自然带出父母住老城区离火车站不远"],
         "plant": [
             {"fact_id": "F9", "hint": f"说下下周要去{trip}出差，待三天，有个重要方案要当面过"},
             {"fact_id": "F10", "hint": f"说出差完顺路回老家{hometown}一趟，离{trip}高铁方便，好久没见爸妈了"},
             {"fact_id": "F11", "hint": f"说上次说的那个{body}复查没事了，医生说可以慢慢恢复{h}，别一下子加量"},
             {"fact_id": "F3", "hint": "提到爸妈就住老城区那片，离火车站不远"},
         ], "messages": []},
        {"session_id": "s4", "date": d["s4"].isoformat(), "date_cn": cn(d["s4"]), "weekday": WEEKDAYS[d["s4"].weekday()],
         "design_notes": ["口语表达", f"新事实：{short}/{g}/乳糖不耐", "干扰事实：瞒着父母"],
         "phenomena": ["第一条user消息自然带出会话日期", "口语化表达，避免翻译腔"],
         "plant": [
             {"fact_id": "F13", "hint": f"说报了个{cls}，每周{d1}上课，从零开始学"},
             {"fact_id": "F14", "hint": f"说{d['month']}月底要去{gplace}考{g}，{prep}，就等实操"},
             {"fact_id": "F12", "hint": "说自己乳糖不耐，喝奶茶都得换燕麦奶，让助手推荐饮品避开牛奶"},
             {"fact_id": "F15", "hint": f"说考{g}这事别跟爸妈提，怕他们念叨，先瞒着"},
         ], "messages": []},
        {"session_id": "s5", "date": d["s5"].isoformat(), "date_cn": cn(d["s5"]), "weekday": WEEKDAYS[d["s5"].weekday()],
         "design_notes": ["相对时间：昨天→需锚定到会话日期", f"三条更新链收口：{h}/{short}/{g}", "模糊时间：下个月", "指代：记得我的过敏和乳糖问题"],
         "phenomena": ["第一条user消息自然带出会话日期", "相对时间：昨天考下了证（助手禁止换算成绝对日期）", "模糊时间：下个月父母来", "指代：记得我的过敏和乳糖问题"],
         "plant": [
             {"fact_id": "F18", "hint": f"说昨天{g}考下来了，一次过，很高兴（只说昨天，不说绝对日期）"},
             {"fact_id": "F16", "hint": f"说{body}彻底好了，这周开始又{h}了，还是原来那条线，循序渐进慢慢加量"},
             {"fact_id": "F17", "hint": f"说{cls}调时间了，{reason}，从这周起改到{d2}"},
             {"fact_id": "F19", "hint": f"说下个月爸妈要来{work}住一阵，让助手推荐适合老人的清淡餐厅，记得自己的过敏和乳糖问题"},
         ], "messages": []},
    ]

    em = EVAL_DATE.month
    questions = [
        {"qid": f"zh_{index:03d}_q01", "type": "single_hop", "question": f"{name}对什么过敏？",
         "answer": f"{allergy['name']}。{allergy['detail']}。", "evidence_sessions": ["s1"], "evidence_facts": ["F4"],
         "scoring": f"答案必须包含{allergy['name']}。"},
        {"qid": f"zh_{index:03d}_q02", "type": "single_hop", "question": f"{name}喝奶茶时为什么要把牛奶换成燕麦奶？",
         "answer": "因为乳糖不耐，需要避开牛奶。", "evidence_sessions": ["s4"], "evidence_facts": ["F12"],
         "scoring": "必须指出乳糖不耐或不能消化牛奶；回答偏好或口味原因判错。"},
        {"qid": f"zh_{index:03d}_q03", "type": "multi_hop", "question": f"{name}{trip}出差结束后顺路探亲，父母住在哪个城市的哪个区域？",
         "answer": f"{hometown}老城区，离火车站不远。", "evidence_sessions": ["s1", "s3"], "evidence_facts": ["F3", "F10"],
         "scoring": f"必须包含{hometown}；答出老城区为完整。需组合s1老家信息与s3住址细节。"},
        {"qid": f"zh_{index:03d}_q04", "type": "multi_hop", "question": f"{name}{body}受伤不能{h}的那段时间，改用什么方式锻炼？",
         "answer": f"{sub}。", "evidence_sessions": ["s1", "s2"], "evidence_facts": ["F5", "F6", "F7"],
         "scoring": f"必须回答{sub}；回答其他运动判错。"},
        {"qid": f"zh_{index:03d}_q05", "type": "temporal", "question": f"{name}是几月几号考下{g}的？",
         "answer": f"{full(d['completion'])}。", "evidence_sessions": ["s5"], "evidence_facts": ["F18"],
         "scoring": f"接受{cn(d['completion'])}或{full(d['completion'])}；回答{cn(d['s5'])}（未把昨天换算）或{em}月（锚定到运行日）判错。"},
        {"qid": f"zh_{index:03d}_q06", "type": "temporal", "question": f"{name}{cn(d['s3'])}说的下下周去{trip}出差，具体是哪一周？",
         "answer": f"{full(tm)}至{trip_end}那一周，即{tm.month}月{xun}。", "evidence_sessions": ["s3"], "evidence_facts": ["F9"],
         "scoring": f"接受{cn(tm)}那一周或{tm.month}月{xun}；回答{em}月（把下下周锚定到add运行日而非会话日期）是典型失败模式，判错。"},
        {"qid": f"zh_{index:03d}_q07", "type": "update", "question": f"{name}现在每周几上{short}课？",
         "answer": f"{d2}。原来是{d1}，{d['s5'].month}月底因{reason}调整。", "evidence_sessions": ["s4", "s5"], "evidence_facts": ["F13", "F17"],
         "scoring": f"必须回答{d2}；回答{d1}判错（未应用知识更新）。"},
        {"qid": f"zh_{index:03d}_q08", "type": "update", "question": f"{name}现在还{h}吗？",
         "answer": f"还{h}。{body}痊愈后已于{d['s5'].month}月底恢复；中间曾因{dis}暂停改{sub}。", "evidence_sessions": ["s1", "s2", "s3", "s5"], "evidence_facts": ["F5", "F6", "F16"],
         "scoring": f"必须明确已恢复{h}；回答不{h}或还在{sub}判错（未应用更新链最终状态）。"},
        {"qid": f"zh_{index:03d}_q09", "type": "abstention", "question": abstentions[0]["q"].format(name=name),
         "answer": "对话中从未提及，应回答不知道或没有相关记忆。", "evidence_sessions": [], "evidence_facts": [],
         "scoring": "明确表示不知道、未提及或无相关记忆判对；确定性回答判错（幻觉）。"},
        {"qid": f"zh_{index:03d}_q10", "type": "abstention", "question": abstentions[1]["q"].format(name=name),
         "answer": "对话中从未提及，应回答不知道或没有相关记忆。", "evidence_sessions": [], "evidence_facts": [],
         "scoring": "明确表示不知道、未提及或无相关记忆判对；确定性回答判错（幻觉）。"},
    ]

    return {
        "schema_version": "0.1",
        "user_id": f"zh_{index:03d}",
        "persona": persona,
        "abstention_topics": abstentions,
        "sessions": sessions,
        "facts": facts,
        "questions": questions,
        "eval_config": {
            "reset_before_add": True,
            "add_order": ["s1", "s2", "s3", "s4", "s5"],
            "questions_asked_after": "all_sessions",
            "eval_date": EVAL_DATE.isoformat(),
            "notes": "每个会话作为一次add调用按时间顺序写入。会话文本内含日期锚点，考察抽取模型能否以文本日期而非真实运行日期锚定相对时间。superseded事实在被埋入时仍为真，计入抽取召回率，但回答以最新状态为准。",
        },
    }