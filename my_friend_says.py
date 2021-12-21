from hoshino.typing import CQEvent
from hoshino import Service
import os, random, hoshino, base64, time
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO

sv = Service('我有一个朋友', help_='''
我朋友说[@xx]xxxxxxx
xx酱说xxxxxx
'''.strip())
headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "zh-cn"
           }
           
fontpath = os.path.join(os.path.dirname(__file__), 'msyh.ttc')
head_path = os.path.join(os.path.dirname(__file__), '1.png')
body_path = os.path.join(os.path.dirname(__file__), '2.png')
end_path = os.path.join(os.path.dirname(__file__), '3.png')

tlmt = hoshino.util.DailyNumberLimiter(10)

def check_lmt(uid): #次数限制
    flmt_g = hoshino.util.FreqLimiter(0)
    if uid in hoshino.config.SUPERUSERS:
        return 0, ''
    if uid in hoshino.config.MANAGERS:
        return 0, ''
    if not tlmt.check(uid):
        return 1, "您今天已经呼叫过10次朋友了,朋友累了,请明天再来!"
    tlmt.increase(uid,1)
    return 0, ''

async def get_group_owener_id(bot, group_id): #获取群主qq
    _member_list = await bot.get_group_member_list(group_id = group_id)
    for member in _member_list:
        if member["role"] == "owner":
            _member = member
            break
    return _member['user_id']
     
async def get_group_admin_id(bot, group_id): #获取管理qq
    _member_list = await bot.get_group_member_list(group_id = group_id)
    member_list = []
    for member in _member_list:
        if member['role'] == 'admin':
            member_list.append(member)
    _member = random.choice(member_list)
    return _member['user_id']

async def get_group_member_id(bot, group_id, sex): #获取qq号列表，排除掉长时间（大约30天）不活跃的群友
    _member_list = await bot.get_group_member_list(group_id = group_id)
    member_list = []
    now = time.time()
    for member in _member_list:
        if sex == '' or sex == member['sex'] or member['sex'] == 'unknown':
            if now - member['last_sent_time'] < 2500000:
                member_list.append(member)
    _member = random.choice(member_list)
    return _member['user_id']
        
async def request_img(uid):
    response = await hoshino.aiorequests.get(f' http://q1.qlogo.cn/g?b=qq&nk={uid}&s=100', headers=headers)
    image = Image.open(BytesIO(await response.content))
    image = image.resize((125, 125), Image.ANTIALIAS)
    return image

def strQ2B(c):  #全角全部强制转半角（懒得处理全角符号的长度了）
    _c = ord(c)
    if _c == 12288:
        _c = 32
    elif 65281 <= _c <= 65374:
        _c -= 65248
    return chr(_c)

def remake_text(text): #对文本重新分行
    temp = ''
    len_ = 0
    text_list = []
    for i in text:
        if i == '\n':
            text_list.append(temp)
            len_ = 0
            temp = ''
            continue
        else:
            i = strQ2B(i)
            temp += i
        if '\u4e00' <= i <= '\u9fff':
            len_ += 50
        else:
            len_ += 26
        if len_ >= 611:
            text_list.append(temp)
            len_ = 0
            temp = ''
    if temp != '':
        text_list.append(temp)
    return text_list

async def make_pic(uid,text,name):
    padding = [230,120]
    font = ImageFont.truetype(fontpath, 48)
    font_name = ImageFont.truetype(fontpath, 42)
    
    head = Image.open(head_path)
    draw = ImageDraw.Draw(head)
    draw.text((220, 18), name, font = font_name, fill = (123,128,140))
    
    body = Image.open(body_path)
    end = Image.open(end_path)
    
    text_list = remake_text(text)
    icon = await request_img(uid)
    
    wa = head.size[0]
    ha = 205 + len(text_list) * 53
    
    i = Image.new('RGB', (wa, ha), color=(255, 255, 255))
    i.paste(icon,(40,27))
    if len(text_list) == 1:
        i.paste(end,(0,ha-end.size[1]))
        i.paste(head,(0,0),head)
    else:
        body = body.resize((wa,ha-head.size[1]-end.size[1]), Image.ANTIALIAS)
        i.paste(head,(0,0),head)
        i.paste(body,(0,head.size[1]))
        i.paste(end,(0,head.size[1]+body.size[1]))
    draw = ImageDraw.Draw(i)
    for j in range(len(text_list)):
        text = text_list[j]
        draw.text((padding[0], padding[1] + 53 * j), text, font = font, fill = (0, 0, 0))

    buf1 = BytesIO()
    i.save(buf1, format='PNG')
    base64_str1 = f'base64://{base64.b64encode(buf1.getvalue()).decode()}'
    msg1 = f'''[CQ:image,file={base64_str1}]'''
    
    return msg1

def sex_get(text):
    sex = ''
    if text[0] == '他': #简单的识别一下朋友性别
        sex = 'male'
    elif text[0] == '她':
        sex = 'female'
    _text = ''
    for i in text: #谓词转换，不需要可以注释掉
        if i in ['他', '她']:
            _text += '我'
            continue
        elif i == '我':
            _text += '你'
            continue
        elif i == '你':
            _text += '他'
            continue
        else:
            _text += i

    return sex, _text


@sv.on_prefix('我朋友说')
async def my_friend_say(bot, ev):
    user_id = ev.user_id
    flag, msg = check_lmt(user_id)
    if flag:
        await bot.send(ev, msg, at_sender = True)
        return
    gid = ev.group_id
    uid = 0
    text = ''
    for msg in ev.message:
        if msg.type == 'at':
            uid = msg.data['qq']
            continue
        elif msg.type == 'text':
            text = msg.data['text'].strip()
    if text == '':
        return
    else:
        sex, text = sex_get(text)
    if uid == 0:
        uid = await get_group_member_id(bot, gid, sex)
    msg = await make_pic(uid,text,'朋友')
    await bot.send(ev, msg)
    

@sv.on_rex(r'^(.*)酱说(.*)')
async def group_owner_say(bot, ev):
    user_id = ev.user_id
    flag, msg = check_lmt(user_id)
    if flag:
        await bot.send(ev, msg, at_sender = True)
        return
    gid = ev.group_id
    name = str.strip(ev['match'].group(1))
    text = str.strip(ev['match'].group(2))
    if text == '':
        return
    else:
        sex, text = sex_get(text)
    if name == '群主':
        uid = await get_group_owener_id(bot, gid)
    elif name == '管理':
        uid = await get_group_admin_id(bot, gid)
    else:
        uid = await get_group_member_id(bot, gid, sex)
    msg = await make_pic(uid,text,name)
    await bot.send(ev, msg)
