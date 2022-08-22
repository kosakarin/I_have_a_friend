from hoshino.typing import CQEvent
from hoshino import Service
import os, random, hoshino, base64, time
from PIL import Image, ImageFont, ImageDraw
from io import BytesIO

sv = Service('我有一个朋友', help_='''
我朋友说[@xx]xxxxxxx
[@xx]xx酱说xxxxxx
'''.strip())
headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "zh-cn"
           }
           
fontpath = os.path.join(os.path.dirname(__file__), 'msyh.ttc')
head_path = os.path.join(os.path.dirname(__file__), '1.png')
body_path = os.path.join(os.path.dirname(__file__), '2.png')
end_path = os.path.join(os.path.dirname(__file__), '3.png')
short_path_left = os.path.join(os.path.dirname(__file__), 'talk_short_left.png')
short_path_right = os.path.join(os.path.dirname(__file__), 'talk_short_right.png')
short_path_head_img = os.path.join(os.path.dirname(__file__), 'talk_head_img.png')
tlmt = hoshino.util.DailyNumberLimiter(10)
max_len = 651

def check_lmt(uid): #次数限制
    flmt_g = hoshino.util.FreqLimiter(0)
    if uid in hoshino.config.SUPERUSERS:
        return 0, ''
    if not tlmt.check(uid):
        return 1, "您今天已经呼叫过10次朋友了,朋友累了,请明天再来!"
    tlmt.increase(uid,1)
    return 0, ''

async def member_list_load(bot,gid):
    _list = await bot.get_group_member_list(group_id = gid)
    return _list

class IDloader:
    def __init__(self, bot, ev, member_list, mode=1):
        self.group_id = ev.group_id
        self.member_list = member_list
        self.owner_id = self.get_group_owener_id()
        self.admin_list = self.get_group_admin_id()
        self.active_member_list = self.get_group_member_id()
        self.at_qq, self.at_name = self.load_at(ev)
        if mode == 1:
            self.text = self.load_text_prefix(ev)
        elif mode == 2:
            self.text = self.load_text_match(ev)

    def get_group_owener_id(self): #获取群主qq
        for member in self.member_list:
            if member["role"] == "owner":
                return member['user_id']
        else:
            return None
    
    def get_group_admin_id(self): #获取管理qq
        member_list = []
        for member in self.member_list:
            if member['role'] == 'admin':
                member_list.append(member['user_id'])
        return member_list
    
    def get_group_member_id(self): #获取qq号列表，排除掉长时间（大约30天）不活跃的群友
        member_list = []
        now = time.time()
        for member in self.member_list:
            if now - member['last_sent_time'] < 2500000:
                member_list.append(member)
        return member_list
        
    def choice_random_member(self, sex=''): #根据性别随机获得群员qq
        temp = []
        for member in self.active_member_list:
            if sex == '' or sex == member['sex'] or member['sex'] == 'unknown':
                temp.append(member['user_id'])
        return random.choice(temp)
       
    def load_at(self, ev): #从消息中提取at信息
        try:
            for msg in ev.message:
                if msg.type == 'at':
                    uid = int(msg.data['qq'])
                    for member in self.member_list:
                        if member['user_id'] == uid:
                            name = member['card'] if member['card'] else member['nickname']
                            break
                    return uid, name
            else:
                return None, None
        except Exception as e:
            print(repr(e))
            return None, None
    
    def load_text_match(self, ev):
        match = ev.match
        self.name = str.strip(ev['match'].group(1))
        if not self.at_qq:
            for member in self.member_list:
                if (member['card'] and member['card'] == self.name) or member['nickname'] == self.name:
                    self.at_qq = member['user_id']
        return str.strip(ev['match'].group(2))
        
    def load_text_prefix(self, ev):
        return ev.message.extract_plain_text().strip()
        
async def request_img(uid):
    response = await hoshino.aiorequests.get(f' http://q1.qlogo.cn/g?b=qq&nk={uid}&s=100', headers=headers)
    image = Image.open(BytesIO(await response.content))
    image = image.resize((125, 125), Image.ANTIALIAS)
    return image

def strQ2B(c):  #全角全部强制转半角（懒得处理全角符号的长度了）
    if c == '\u200b':
        return ' '
    _c = ord(c)
    if _c == 12288:
        _c = 32
    elif 65281 <= _c <= 65374:
        _c -= 65248
    return chr(_c)

def get_char_len(i):
        if '\u4e00' <= i <= '\u9fff' or i in ['、','—','“','”','《','》','【','】','。','@']:
            return 50
        else:
            return 26

def get_text_len(text):
    len_ = 0
    for i in text:
        len_ += get_char_len(i)

    return len_

def is_en(i):
    if '\u0061' <= i <= '\u007A' or '\u0041' <= i <= '\u005A':
        return 1
    else:
        return 0

def remake_text(text): #对文本重新分行 
    temp = ''
    word_temp = ''
    len_ = 0
    text_list = []
    for i in text:
        if is_en(i): #保证英语单词不被分割
            word_temp += i
            continue
        elif word_temp != '':
            word_len = 26 * len(word_temp)
            if word_len >= max_len:  #本身大于一行，无视整词规则，重新分割；
                char_len = 26
                for i_ in word_temp:
                    if len_ + char_len >= max_len:
                        text_list.append(temp)
                        len_ = char_len
                        temp = i_
                    else:
                        len_ += char_len
                        temp += i_
                else:
                    word_temp = ''
            elif word_len + len_ >= max_len:
                text_list.append(temp)
                len_ = word_len
                temp = word_temp
                word_temp = ''
            else:
                temp += word_temp
                word_temp = ''
                len_ += word_len
                
        #触发elif后 当前字符还未操作，继续操作
        if i == '\n':
            text_list.append(temp)
            len_ = 0
            temp = ''
            continue
        else:
            i = strQ2B(i)
            
        char_len = get_char_len(i)
        
        if len_ + char_len >= max_len:
            text_list.append(temp)
            len_ = char_len
            temp = i
        else:
            len_ += char_len
            temp += i
    else:
        if word_temp != '':
            word_len = 26 * len(word_temp)
            if word_len >= max_len:  #本身大于一行，无视整词规则，重新分割；
                char_len = 26
                for i_ in word_temp:
                    if len_ + char_len >= max_len:
                        text_list.append(temp)
                        len_ = char_len
                        temp = i_
                    else:
                        len_ += char_len
                    temp += i_
                else:
                    word_temp = ''
            elif word_len + len_ >= max_len:
                text_list.append(temp)
                temp = word_temp
            else:
                temp += word_temp

    
    if temp != '':
        text_list.append(temp)
    return text_list
async def make_pic(uid,text,name):
    padding = [230,120]
    font = ImageFont.truetype(fontpath, 48)
    font_name = ImageFont.truetype(fontpath, 42)
    
    text_list = remake_text(text)
    icon = await request_img(uid)
    wa = 1079  #这个就是旧版3张图片的长度
    ha = 205 + len(text_list) * 53
    i = Image.new('RGB', (wa, ha), color=(234, 237, 244))
    i.paste(icon,(40,27))
    
    if len(text_list) == 1:
        len_ = get_text_len(text)
        draw = ImageDraw.Draw(i)
        draw.text((220, 18), name, font = font_name, fill = (123,128,140))
        left = Image.open(short_path_left)
        right = Image.open(short_path_right)
        head_img = Image.open(short_path_head_img)
        if len_ > 60:
            body = Image.new('RGB', ((len_ - 60), 125), color=(255, 255, 255))
            i.paste(head_img,(0,0),head_img)
            i.paste(left,(182,95),left)
            i.paste(body,(267,96))
            i.paste(right,(257 + (len_ - 59),95),right)
        else:
            i.paste(head_img,(0,0),head_img)
            i.paste(left,(182,95),left)
            i.paste(right,(257,95),right)
    else:
        head = Image.open(head_path)
        draw = ImageDraw.Draw(head)
        draw.text((220, 18), name, font = font_name, fill = (123,128,140))
    
        body = Image.open(body_path)
        end = Image.open(end_path)
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
    member_list = await member_list_load(bot,ev.group_id)
    info = IDloader(bot, ev, member_list, 1)
    if info.text == '':
        return
    else:
        sex, text = sex_get(info.text)
        uid = info.at_qq if info.at_qq else info.choice_random_member(sex)
    msg = await make_pic(uid,text,'朋友')
    await bot.send(ev, msg)

@sv.on_rex(r'^(.*)酱说(.*)')
async def group_owner_say(bot, ev):
    user_id = ev.user_id
    flag, msg = check_lmt(user_id)
    if flag:
        await bot.send(ev, msg, at_sender = True)
        return
    member_list = await member_list_load(bot,ev.group_id)
    info = IDloader(bot, ev, member_list, 2)
    name = info.name if info.name else info.at_name
    text = info.text
    if text == '':
        return
    else:
        sex, text = sex_get(text)
    if info.at_qq:
        uid = info.at_qq
    elif name == '群主':
        uid = info.owner_id
    elif name == '管理':
        uid = random.choice(info.admin_list)
    else:
        uid = info.choice_random_member(sex)
    msg = await make_pic(uid,text,name)
    await bot.send(ev, msg)
