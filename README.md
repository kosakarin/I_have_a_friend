# I_have_a_friend
我朋友说他什么都没说

# 已适配短句时的聊天框缩短（虽然没细节到每一个像素都完美对应）

然后群友讨论的时候问能不能做xx说xxx之后bot生成直接的聊天记录而不是图片（本意是开玩笑因为有人迫害了群友后那个群友把被迫害的内容复读了一遍，如下图），其实利用转发消息接口是能做的，虽然我不太愿意做，如果有人需要的话提个issue我写进这个里面

![image](https://user-images.githubusercontent.com/91523573/180747395-31450e11-d65c-4490-9b3e-55a6f9bb5bc6.png)


## 我记得以前好像有这个功能的，但是我突然就找不到了，然后就自己写了个emmmm，有没有好哥哥给我讲下在哪个仓库里来着，反正我这个用的是群聊的模板，理论上可以生成无限的长度，也不算重复功能了

## 如果报错提示缺少字体文件，去我其他仓库下面下载一下msyh.tcc这个字体放在同目录下即可，或者用其它字体也可以

## 用法

分为两个触发器

我朋友说(@xx) xxxx  @xx可以省略，略去则随机选取头像，固定名称为‘朋友’

(@xx)aa酱说xxxxx 可以指定昵称和头像，略去@xx则根据aa来匹配头像，匹配失败转为随机选取，略去aa则根据@选取头像和昵称，对于头像的选择，@优先级较高，昵称则aa的优先级更高

由于代码中存在谓词转换规则，“他”or“她”会被转换成“我”，“你”会被转换成“他”，“我”会被转成“你”，如果觉得麻烦可以去注释掉那一小段
