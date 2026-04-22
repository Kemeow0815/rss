# -*- coding: utf-8 -*-
import os
import json
import time
import feedparser

######################################################################################
displayDay=30 # 抓取多久前的内容
displayMax=5 # 每个RSS最多抓取数
weeklyKeyWord="" # 周刊过滤关键字

rssBase={
    "张洪heo":{
        "url":"https://blog.zhheo.com/rss.xml",
        "type":"post",
        "timeFormat":"%a, %d %b %Y %H:%M:%S GMT",
        "nameColor":"#a4244b"
    },
    "二叉树树":{
        "url":"https://2x.nz/rss.xml",
        "type":"post",
        "timeFormat":"%a, %d %b %Y %H:%M:%S GMT",
        "nameColor":"#feca57"
    },
    "柳神":{
        "url":"https://blog.liushen.fun/atom.xml",
        "type":"post",
        "timeFormat":"%Y-%m-%dT%H:%M:%S.%fZ",
        "nameColor":"#48dbfb"
    },
    "二叉树树":{
        "url":"https://2x.nz/rss.xml",
        "type":"post",
        "timeFormat":"%a, %d %b %Y %H:%M:%S GMT",
        "nameColor":"#feca57"
    },
    "CWorld":{
        "url":"https://cworld0.com/rss.xml",
        "type":"post",
        "timeFormat":"%a, %d %b %Y %H:%M:%S GMT",
        "nameColor":"#9b59b6"
    },
    "Saneko":{
        "url":"https://saneko.me/rss.xml",
        "type":"post",
        "timeFormat":"%a, %d %b %Y %H:%M:%S GMT",
        "nameColor":"#e74c3c"
    },
    "纸鹿本鹿":{
        "url":"https://blog.zhilu.site/atom.xml",
        "type":"post",
        "timeFormat":"%Y-%m-%dT%H:%M:%SZ",
        "nameColor":"#2ecc71"
    },
    "絮语":{
        "url":"https://www.wxuyu.top/atom.xml",
        "type":"post",
        "timeFormat":"%Y-%m-%dT%H:%M:%SZ",
        "nameColor":"#f39c12"
    },
}
######################################################################################

rssAll=[]
info=json.loads('{}')
info["published"]=int(time.time())
info["rssBase"]=rssBase
rssAll.append(info)

displayTime=info["published"]-displayDay*86400

print("====== Now timestamp = %d ======"%info["published"])
print("====== Start reptile Last %d days ======"%displayDay)

for rss in rssBase:
    print("====== Reptile %s ======"%rss)
    rssDate = feedparser.parse(rssBase[rss]["url"])
    i=0
    for entry in rssDate['entries']:
        if i>=displayMax:
            break
        if 'published' in entry:
            published=int(time.mktime(time.strptime(entry['published'], rssBase[rss]["timeFormat"])))

            if entry['published'][-5]=="+":
                published=published-(int(entry['published'][-5:])*36)

            if rssBase[rss]["type"]=="weekly" and (weeklyKeyWord not in entry['title']):
                continue

            if published>info["published"]:
                continue

            if published>displayTime:
                onePost=json.loads('{}')
                onePost["name"]=rss
                onePost["title"]=entry['title']
                onePost["link"]=entry['link']
                onePost["published"]=published
                rssAll.append(onePost)
                print("====== Reptile %s ======"%(onePost["title"]))
                i=i+1
        else:
            published = None
            print("Warning: 'published' key not found in entry")

            
print("====== Start sorted %d list ======"%(len(rssAll)-1))
rssAll=sorted(rssAll,key=lambda e:e.__getitem__("published"),reverse=True)

if not os.path.exists('docs/'):
    os.mkdir('docs/')
    print("ERROR Please add docs/index.html")

listFile=open("docs/rssAll.json","w")
listFile.write(json.dumps(rssAll))
listFile.close()
print("====== End reptile ======")
######################################################################################
