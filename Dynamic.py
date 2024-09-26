import pyqrcode
import requests
import requests.utils
import os
import time
import subprocess
import json
import csv
import sys
from datetime import datetime
from lxml import etree

requests.packages.urllib3.disable_warnings()

#主文件夹
BASEDIR = os.path.dirname(os.path.realpath( sys.argv[0]))
type = sys.getfilesystemencoding()
print(type)
class Dynamic:
    CONFIG = {}
    # 数据格式
    datajson = {'id':'','aid':'','comment_type':'','type':'','title':'','text':'','imagepath':'','videopath':''}

    def main(self):
        self.init()
        self.start()

    
    def setconfig(self):
        with open(BASEDIR+'/config.json', 'w',encoding='utf-8') as f:
            json.dump(self.CONFIG, f)


    #初始化方法，访问主站后拼接headers
    def init(self):
        self.dyidlist = {}
        self.dir_path = BASEDIR
        self.sess = requests.Session()
        json_path = os.path.join(BASEDIR, "config.json")
        with open(json_path,'r',encoding='utf-8') as jf:
            self.CONFIG = json.load(jf)
            # self.isec = CONFIG['interval-sec']
            # self.autodownload = CONFIG['autodownload']
            # self.downatfirst = self.CONFIG['down-atfirst']
            # self.bupid = CONFIG['bupid']
            # self.islog = CONFIG['islog']
            # self.message = CONFIG['autocomment']
            # headers = CONFIG['headers']
            # 刚开始运行不评论，只有检测到更新时才评论
        self.iscomment = False

        if (self.CONFIG['datadir'] != ''):
            self.dir_path = self.CONFIG['datadir']
            # 如果目录不存在，则创建目录
            if not os.path.exists(self.dir_path): os.makedirs(self.dir_path)

        self.log(self.CONFIG['headers'])
        self.sess.headers = self.CONFIG['headers']
        # 判断是否需要登录
        if (self.CONFIG['Cookies'] == '' or self.CONFIG['Cookies'] == {}) :
            self.log("登录-----")
            self.login()
        else :
            self.log("从config设置Cookies")
            self.sess.cookies = requests.utils.cookiejar_from_dict(self.CONFIG['Cookies'])
        d = self.sess.get('https://api.bilibili.com/x/web-interface/nav').json()
        if not d['data']['isLogin'] : self.login()
        self.log(self.CONFIG)
        for up in self.CONFIG['bupid']:
            self.updylist(up)

# 登陆方法

    def login(self):
        cook = {}
        a = self.sess.get('https://www.bilibili.com')
        
        for co in self.sess.cookies:
            cook[co.name] = co.value
            self.log(co.value)
        rep = self.sess.get('https://passport.bilibili.com/x/passport-login/web/qrcode/generate')
        print("Request Headers:")
        print(self.sess.headers)

        # 打印响应的 headers
        print("\nResponse Headers:")
        print(rep.headers)

        # 打印 cookies
        print("\nCookies:")
        print(self.sess.cookies)
        print("Content Type:", rep.headers.get('Content-Type'))

        self.log(rep.text)
        rep=rep.json()

        qrcode = rep['data']['url']
        token = rep['data']['qrcode_key']
        pyqrcode.create(qrcode).png((BASEDIR + '/qrcode.png'),scale=12)
        os.startfile((BASEDIR + '/qrcode.png'))
        while True:
            rst = self.sess.get('https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key='+token)
            j=rst.json()
            if j['data']['code'] == 0:
                self.log('登录成功')
                self.CONFIG['refresh_token'] = j['data']['refresh_token']
                for co in rst.cookies:
                    cook[co.name] = co.value
                self.CONFIG['Cookies'] = cook
                self.setconfig()
                os.remove(BASEDIR + '/qrcode.png')
                return
            time.sleep(3)










    def start(self):
        while True :
            for upid in self.CONFIG['bupid']:
                self.getdata(upid=upid)
            
            self.iscomment = True
            self.log('up id列表已更新 + 开始自动评论')
            self.CONFIG['down-atfirst'] = self.CONFIG['autodownload']
            time.sleep(self.CONFIG['interval-sec'])

    #从csv中获取已缓存的动态id列表，判断重复或更新写入csv
    def updylist(self,upid):
        self.dyidlist[upid]=[]
        file_path = os.path.join(self.dir_path, '{0}/{0}.csv'.format(upid))
        try:
            with open(file=file_path ,mode='r') as c:
                r = csv.DictReader(c)
                for ro in r:
                    self.dyidlist[upid].append(ro['id'])
        except FileNotFoundError:
            self.log('首次运行')
            return
        self.CONFIG['down-atfirst'] = self.CONFIG['autodownload']

    def getdata(self,upid):
        url = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space'
        params = { 
            'host_mid': upid            
        }
        data = self.sess.get(url=url,params=params).json()
        # 未成功获取情况
        if data['code'] != 0 :
            self.log(data)
            #刷新下初始数据
            self.init()
            return
        
        try :
            dytype = data['data']['items'][0]['modules']['module_tag']['text']
        except KeyError:
            self.log('up[{0}] 无置顶动态'.format(upid))
            dytype = ''
         # 如果数据第一条是置顶动态，那么暴力计算前两条是否是更新的
        if(dytype=='置顶'):
            if(self.dyidlist[upid] != [] and ( data['data']['items'][0]['id_str'] in self.dyidlist[upid] and data['data']['items'][1]['id_str'] in self.dyidlist[upid])  ):
                self.log('====')
                return      
        # 如果没有更新，return
        elif(self.dyidlist[upid] != [] and data['data']['items'][0]['id_str'] == self.dyidlist[upid][-1] ):
            self.log('====')
            return
        
        for item in data['data']['items'][::-1] :

            dali = self.toDynamicData(item)
            try:
            # 如果该动态已经获取，退出
                if(dali['id'] in self.dyidlist[upid]):                   
                    continue
            except Exception:
                self.log('QAQ')

            self.log('Data= id:{0},text:{1},imagepath:{2},videopath:{3},type:{4}'.format(dali['id'],dali['text'],dali['imagepath'],dali['videopath'],dali['type']))

            csv_path  = os.path.join(self.dir_path, '{0}/{0}.csv'.format(upid))
            folder_path = os.path.dirname(csv_path)
            # 如果文件夹不存在，创建文件夹
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            # 如果文件不存在，创建文件
            try:
                
                # if not os.path.isfile(csv_path):
                #     with open(file=csv_path ,mode='a',encoding='gbk', newline='') as c:
                #         w = csv.DictWriter(c,fieldnames=self.datajson.keys(),quoting=csv.QUOTE_ALL)
                #         w.writeheader()
                #         self.log(dali)
                #         w.writerow(dali)
                # else:
                #     with open(file=csv_path ,mode='a',encoding='gbk', newline='') as c:
                #         csv.DictWriter(c,fieldnames=self.datajson.keys(),quoting=csv.QUOTE_ALL).writerow(dali)


                if not os.path.isfile(csv_path):
                    with open(file=csv_path ,mode='a',encoding='gbk',errors='ignore', newline='') as c:
                        w = csv.DictWriter(c,fieldnames=self.datajson.keys(),quoting=csv.QUOTE_ALL)
                        w.writeheader()
                        self.log(dali)
                        w.writerow(dali)
                else:
                    with open(file=csv_path ,mode='a',encoding='gbk',errors='ignore', newline='') as c:
                        csv.DictWriter(c,fieldnames=self.datajson.keys(),quoting=csv.QUOTE_ALL).writerow(dali)
                    
            
            except PermissionError:
                self.log('权限不足写入失败，或许其他程序占用')
            
            # 自动评论
            if self.iscomment and self.CONFIG['autocomment'] != '' : self.commentaction(dali['comment_type'],dali['aid'])
            #第一次不缓存则跳过
            if not self.CONFIG['down-atfirst'] : continue
            # 设置不自动下载附件则跳过
            if not self.CONFIG['autodownload'] : continue
            self.downimage(upid,dali['id'],dali['imagepath'])
            self.downvideo(upid,dali['videopath'])    
        # 更新已缓存id列表
        self.updylist(upid)








    def downimage(self,upid,id,path):
        if path == '' : return

        for index,url  in enumerate(path):
            a = str(url).split('.')[-1]
            img_path = os.path.join(self.dir_path, f'{upid}/{id}_00{index+1}.{a}')
            img = self.sess.get(url).content
            with open(img_path,'wb') as file:
                file.write(img)

    def downvideo(self,upid,url):
        if url == '' : return

        bvid = str(url).split('/')[-2]
        res = self.sess.get(url=url)
        _element = etree.HTML(res.content)
        videoPlayInfo = str(_element.xpath('//head/script[4]/text()')[0].encode('utf-8').decode('utf-8'))[20:]
        videoJson = json.loads(videoPlayInfo)
        videoURL = videoJson['data']['dash']['video'][0]['baseUrl']
        audioURL = videoJson['data']['dash']['audio'][0]['baseUrl']

        videoPath = os.path.join(self.dir_path, '{0}/{1}.mp4'.format(upid,bvid))
        audioPath = os.path.join(self.dir_path, '{0}/{1}.mp3'.format(upid,bvid))
        self.downfile(homeurl=url,url=videoURL,filepath=videoPath,session=self.sess)
        self.downfile(homeurl=url,url=audioURL,filepath=audioPath,session=self.sess)

        videoout = os.path.join(self.dir_path, '{0}/{1}_out.mp4'.format(upid,bvid))
        self.combineVideoAudio(videoPath,audioPath,videoout,bvid)

        
    def combineVideoAudio(self,videopath,audiopath,outpath,bvid):
        dir = BASEDIR[0].upper() + BASEDIR[1:]
        dir = dir.replace("\\","/")
        #subprocess.call((dir +"/ffmpeg/bin/ffmpeg.exe -y -i " + videopath + " -i " + audiopath + " -c copy "+ outpath).encode("utf-8").decode("utf-8"),shell=True)
        subprocess.run(dir +"/ffmpeg/bin/ffmpeg.exe -y -i " + videopath + " -i " + audiopath + " -c copy "+ outpath,shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.log("下载视频[ {0} ]完成。".format(bvid))
        os.remove(videopath)
        os.remove(audiopath)


    def downfile(self,homeurl,url,filepath,session = requests.session()):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.33',
            'Refer'
            'er': 'https://www.bilibili.com/'
        }
        headers.update({'Referer': homeurl})
        # 发送option请求服务器分配资源
        session.options(url=url, headers=headers,verify=False)
        # 指定每次下载1M的数据
        begin = 0
        end = 1024*512 - 1
        flag = 0
        while True:
            # 添加请求头键值对,写上 range:请求字节范围
            headers.update({'Range': 'bytes=' + str(begin) + '-' + str(end)})
            # 获取视频分片
            res = session.get(url=url, headers=headers,verify=False)
            if res.status_code != 416:
                # 响应码不为为416时有数据
                begin = end + 1
                end = end + 1024*512
            else:
                headers.update({'Range': str(end + 1) + '-'})
                res = session.get(url=url, headers=headers,verify=False)
                flag=1
            with open(filepath, 'ab') as fp:
                fp.write(res.content)
                fp.flush()

            if flag==1:
                fp.close()
                break



    def toDynamicData(self,item):
        # 获取动态json的最终data格式
        da = self.datajson.copy()
        type = item['type']
        da['id'] = item['id_str']
        da['aid'] = item['basic']['comment_id_str']
        da['comment_type'] = item['basic']['comment_type']
        da['type'] = item['type']
        # 根据不同动态类型，处理数据
        # type: DYNAMIC_TYPE_AV 视频, DYNAMIC_TYPE_WORD 文字动态, DYNAMIC_TYPE_DRAW 图文动态, DYNAMIC_TYPE_ARTICLE 专栏, DYNAMIC_TYPE_FORWARD 转发动态

        if (type == 'DYNAMIC_TYPE_AV' ) : 
            a=''
            try: 
                a= item['modules']['module_dynamic']['desc']['text']
            except:
                pass
            if a != '' :  a= '【投稿动态】： '+a +'\n\n'
            da['title'] = a + item['modules']['module_dynamic']['major']['archive']['title']
            da['text'] =  item['modules']['module_dynamic']['major']['archive']['desc']
            da['imagepath'] = [item['modules']['module_dynamic']['major']['archive']['cover']]
            da['videopath'] = 'https:'+item['modules']['module_dynamic']['major']['archive']['jump_url']
            return da
            
        elif (type == 'DYNAMIC_TYPE_DRAW') : 
            da['title'] = '图文动态'
            da['text'] = item['modules']['module_dynamic']['desc']['text']
            da['imagepath'] = []
            if (item['modules']['module_dynamic']['major'] != None):
                for img in   在 item['modules']['module_dynamic']['major']['draw']['items']:
                    da['imagepath'].append(img['src'])
            return da
        
        elif (type == 'DYNAMIC_TYPE_WORD') : 
            da['title'] = '文字动态'
            da['text'] = item['modules']['module_dynamic']['desc']['text']
            return da
        elif (type == 'DYNAMIC_TYPE_FORWARD'):
            da['title'] = '转发的动态链接：'+str(item['orig']['id_str'])
            da['text'] = item['modules']['module_dynamic']['desc']['text']
            return da

        else : 
            self.log('暂不支持的动态类型[{0}]'.format(type))
            da['text'] = '暂不支持的类型'
            return da   
    
    def log(self,text):
        try:
            print('[{0}]: {1}\n'.format(datetime.now().strftime('%m/%d %H:%M'),text).encode('utf-8').decode(type))
        except UnicodeEncodeError:
            print("编码错误")
            pass

        if(not self.CONFIG   配置['is_log']):
            return 
        log_path = os.path.join(BASEDIR, "log.txt")
        with open(log_path,'a',encoding='utf-8') as f:
            f.write('[{0}]: {1}\n'.format(datetime.now().strftime('%m/%d %H:%M'),text))


    def commentaction(self,typeid,aid):
        js = {
            'type' : typeid,
            'oid' : aid,
            'message' : '',
            'plat' : 1,
            'csrf' : ''
        }
        js['csrf'] = self.sess.cookies.get('bili_jct')
        js['message'] = self.CONFIG['autocomment'] + '\n\n\n-------' + datetime.now().strftime('%m/%d %H:%M')
        rep = self.sess.post(url='https://api.bilibili.com/x/v2/reply/add',data=js).json()
        
        self.log(' {{ code: {0} , message: {1} }}'.format(rep['code'],rep['message']))
        



if __name__ == '__main__':
    obj = Dynamic()
    obj.main()
