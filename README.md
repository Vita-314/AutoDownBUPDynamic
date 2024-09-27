# AutoDownBUPDynamic
自动检查B站up的更新并缓存图片和视频

基于bilibili-API-collect 项目整理的API开发 
[bilibili-API-collect](https://github.com/SocialSisterYi/bilibili-API-collect)

自动下载视频功能基于知乎用户 程序猿城南 帖子代码
如何使用Python爬取bilibili视频（详细教程） - 知乎 (zhihu.com)
https://zhuanlan.zhihu.com/p/148988473


点击运行，如果没有登录则会在当前目录生成二维码图片并弹窗，打开bilibili app两分钟内扫码登录成功后自动删除本地的二维码图片，手动关闭系统默认的图片程序即可

Config.json 配置：

Headers:浏览器标头数据

Cookies：登录后缓存Cookies

refresh_token: 登录后自动设置，暂无相关代码

bupid：希望自动检查的b站up主id列表，多个用英文 , 隔开

datadir：自定义的缓存数据目录，默认为当前目录，为每个upid的名字

interval-sec:检查周期秒数

autodownload：为true则在检查到up更新后下载图片视频文件

down-atfirst: 为true则在首次运行时下载up动态的文件【*~~暂无效果，因为默认第一次运行只缓存动态列表不下载文件~~*】

autocomment： 自动评论的文字，填入希望检测到up更新后自动评论的内容，为空则不评论

is_log: 为true则在当前目录生成log.txt日志文件
