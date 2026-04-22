# -*- coding: utf-8 -*-
import os
import json
import time
import feedparser
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

######################################################################################
# 基础配置
displayDay = 30  # 抓取多久前的内容
displayMax = 5   # 每个RSS最多抓取数
weeklyKeyWord = ""  # 周刊过滤关键字

# SMTP 邮箱配置（优先从环境变量读取，否则使用默认值）
# QQ 邮箱配置说明：
# - SMTP服务器：smtp.qq.com
# - 端口：465（使用SSL，推荐）或 587（使用TLS）
# - 密码：需要使用QQ邮箱的"授权码"，不是登录密码
# - 授权码获取：QQ邮箱设置 → 账户 → 开启SMTP服务 → 生成授权码
SMTP_CONFIG = {
    "enabled": os.environ.get("SMTP_ENABLED", "false").lower() == "true",
    "smtp_server": os.environ.get("SMTP_SERVER", "smtp.qq.com"),
    "smtp_port": int(os.environ.get("SMTP_PORT", "465")),  # QQ邮箱推荐使用465端口
    "sender_email": os.environ.get("SMTP_SENDER_EMAIL", ""),
    "sender_password": os.environ.get("SMTP_SENDER_PASSWORD", ""),  # QQ邮箱授权码
    "receiver_email": os.environ.get("SMTP_RECEIVER_EMAIL", ""),
}

# GitHub Pages 前端地址
FRONTEND_URL = "https://kemeow0815.github.io/rss/"

# 数据存储路径
DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "rss_history.json")
NEW_ARTICLES_FILE = os.path.join(DATA_DIR, "new_articles.json")

rssBase = {
    "张洪heo": {
        "url": "https://blog.zhheo.com/rss.xml",
        "type": "post",
        "timeFormat": "%a, %d %b %Y %H:%M:%S GMT",
        "nameColor": "#a4244b"
    },
    "二叉树树": {
        "url": "https://2x.nz/rss.xml",
        "type": "post",
        "timeFormat": "%a, %d %b %Y %H:%M:%S GMT",
        "nameColor": "#feca57"
    },
    "柳神": {
        "url": "https://blog.liushen.fun/atom.xml",
        "type": "post",
        "timeFormat": "%Y-%m-%dT%H:%M:%S.%fZ",
        "nameColor": "#48dbfb"
    },
    "CWorld": {
        "url": "https://cworld0.com/rss.xml",
        "type": "post",
        "timeFormat": "%a, %d %b %Y %H:%M:%S GMT",
        "nameColor": "#9b59b6"
    },
    "Saneko": {
        "url": "https://saneko.me/rss.xml",
        "type": "post",
        "timeFormat": "%a, %d %b %Y %H:%M:%S GMT",
        "nameColor": "#e74c3c"
    },
    "纸鹿本鹿": {
        "url": "https://blog.zhilu.site/atom.xml",
        "type": "post",
        "timeFormat": "%Y-%m-%dT%H:%M:%SZ",
        "nameColor": "#2ecc71"
    },
    "闻絮语": {
        "url": "https://www.wxuyu.top/atom.xml",
        "type": "post",
        "timeFormat": "%Y-%m-%dT%H:%M:%SZ",
        "nameColor": "#f39c12"
    },
}
######################################################################################


def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"====== Created data directory: {DATA_DIR} ======")


def load_history():
    """加载历史文章数据"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load history: {e}")
    return []


def save_history(data):
    """保存历史文章数据"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"====== Saved history to {HISTORY_FILE} ======")
    except Exception as e:
        print(f"Error: Failed to save history: {e}")


def load_new_articles():
    """加载上次的新文章列表"""
    if os.path.exists(NEW_ARTICLES_FILE):
        try:
            with open(NEW_ARTICLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load new articles: {e}")
    return []


def save_new_articles(data):
    """保存新文章列表"""
    try:
        with open(NEW_ARTICLES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error: Failed to save new articles: {e}")


def get_article_id(article):
    """生成文章唯一标识"""
    return f"{article.get('name', '')}_{article.get('title', '')}_{article.get('link', '')}"


def find_new_articles(current_articles, history_articles):
    """找出新增的文章"""
    history_ids = {get_article_id(a) for a in history_articles}
    new_articles = []
    for article in current_articles:
        if get_article_id(article) not in history_ids:
            article["isNew"] = True
            new_articles.append(article)
    return new_articles


def remove_old_new_tags(articles, previous_new_articles):
    """移除上次新文章的 NEW! 标签"""
    previous_new_ids = {get_article_id(a) for a in previous_new_articles}
    for article in articles:
        if get_article_id(article) in previous_new_ids:
            article["isNew"] = False
    return articles


def send_email_notification(new_articles):
    """发送邮件通知"""
    if not SMTP_CONFIG["enabled"]:
        print("====== Email notification is disabled ======")
        return

    if not new_articles:
        print("====== No new articles, skip email notification ======")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Gmerss RSS 更新通知 - {len(new_articles)} 篇新文章"
        msg["From"] = SMTP_CONFIG["sender_email"]
        msg["To"] = SMTP_CONFIG["receiver_email"]

        # 构建邮件内容
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2c3e50;">📰 Gmerss RSS 更新通知</h2>
            <p>发现 <strong>{len(new_articles)}</strong> 篇新文章：</p>
            <div style="margin: 20px 0;">
        """

        for article in new_articles:
            pub_time = datetime.fromtimestamp(article.get("published", 0)).strftime("%Y-%m-%d %H:%M")
            html_content += f"""
                <div style="border-left: 4px solid #3498db; padding: 10px 15px; margin: 10px 0; background: #f8f9fa;">
                    <h3 style="margin: 0 0 5px 0; color: #2c3e50;">{article.get('title', '')}</h3>
                    <p style="margin: 5px 0; color: #7f8c8d; font-size: 14px;">
                        👤 {article.get('name', '')} | 📅 {pub_time}
                    </p>
                    <a href="{article.get('link', '')}" style="color: #3498db; text-decoration: none;">阅读原文 →</a>
                </div>
            """

        html_content += f"""
            </div>
            <p style="margin-top: 20px;">
                <a href="{FRONTEND_URL}" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    查看全部文章
                </a>
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #95a5a6; font-size: 12px;">
                此邮件由 Gmerss RSS 自动发送 | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # 发送邮件
        context = ssl.create_default_context()
        
        # 根据端口选择连接方式
        # 465端口使用SSL，587端口使用STARTTLS
        if SMTP_CONFIG["smtp_port"] == 465:
            # SSL连接（QQ邮箱等）
            with smtplib.SMTP_SSL(SMTP_CONFIG["smtp_server"], SMTP_CONFIG["smtp_port"], context=context) as server:
                server.login(SMTP_CONFIG["sender_email"], SMTP_CONFIG["sender_password"])
                server.sendmail(
                    SMTP_CONFIG["sender_email"],
                    SMTP_CONFIG["receiver_email"],
                    msg.as_string()
                )
        else:
            # STARTTLS连接（Gmail等）
            with smtplib.SMTP(SMTP_CONFIG["smtp_server"], SMTP_CONFIG["smtp_port"]) as server:
                server.starttls(context=context)
                server.login(SMTP_CONFIG["sender_email"], SMTP_CONFIG["sender_password"])
                server.sendmail(
                    SMTP_CONFIG["sender_email"],
                    SMTP_CONFIG["receiver_email"],
                    msg.as_string()
                )

        print(f"====== Email notification sent to {SMTP_CONFIG['receiver_email']} ======")
    except Exception as e:
        print(f"Error: Failed to send email: {e}")


def main():
    """主函数"""
    ensure_data_dir()

    # 加载历史数据
    history_articles = load_history()
    previous_new_articles = load_new_articles()

    rssAll = []
    info = json.loads('{}')
    info["published"] = int(time.time())
    info["rssBase"] = rssBase
    rssAll.append(info)

    displayTime = info["published"] - displayDay * 86400

    print("====== Now timestamp = %d ======" % info["published"])
    print("====== Start reptile Last %d days ======" % displayDay)

    for rss in rssBase:
        print("====== Reptile %s ======" % rss)
        try:
            rssDate = feedparser.parse(rssBase[rss]["url"])
            i = 0
            for entry in rssDate['entries']:
                if i >= displayMax:
                    break
                if 'published' in entry:
                    try:
                        published = int(time.mktime(time.strptime(entry['published'], rssBase[rss]["timeFormat"])))

                        if entry['published'][-5] == "+":
                            published = published - (int(entry['published'][-5:]) * 36)

                        if rssBase[rss]["type"] == "weekly" and (weeklyKeyWord not in entry['title']):
                            continue

                        if published > info["published"]:
                            continue

                        if published > displayTime:
                            onePost = json.loads('{}')
                            onePost["name"] = rss
                            onePost["title"] = entry['title']
                            onePost["link"] = entry['link']
                            onePost["published"] = published
                            rssAll.append(onePost)
                            print("====== Reptile %s ======" % (onePost["title"]))
                            i = i + 1
                    except Exception as e:
                        print(f"Warning: Failed to parse date for {entry.get('title', 'unknown')}: {e}")
                else:
                    print("Warning: 'published' key not found in entry")
        except Exception as e:
            print(f"Error: Failed to fetch RSS from {rss}: {e}")

    print("====== Start sorted %d list ======" % (len(rssAll) - 1))
    rssAll = sorted(rssAll, key=lambda e: e.__getitem__("published"), reverse=True)

    # 找出新文章
    new_articles = find_new_articles(rssAll[1:], history_articles)  # 跳过 info 项

    # 如果有新文章，移除上次新文章的 NEW! 标签，并为新文章添加标记
    if new_articles:
        print(f"====== Found {len(new_articles)} new articles ======")
        # 移除上次新文章的 NEW! 标签
        rssAll[1:] = remove_old_new_tags(rssAll[1:], previous_new_articles)
        # 为本次新文章添加标记
        for article in rssAll[1:]:
            if get_article_id(article) in {get_article_id(a) for a in new_articles}:
                article["isNew"] = True
        # 发送邮件通知
        send_email_notification(new_articles)
    else:
        print("====== No new articles found ======")
        # 没有新文章，保留上次的 NEW! 标签
        for article in rssAll[1:]:
            if get_article_id(article) in {get_article_id(a) for a in previous_new_articles}:
                article["isNew"] = True

    # 保存新文章列表（用于下次移除 NEW! 标签）
    save_new_articles([a for a in rssAll[1:] if a.get("isNew", False)])

    # 保存历史数据
    save_history(rssAll[1:])

    # 确保 docs 目录存在
    if not os.path.exists('docs/'):
        os.mkdir('docs/')
        print("ERROR Please add docs/index.html")

    # 保存到 docs/rssAll.json
    listFile = open("docs/rssAll.json", "w", encoding="utf-8")
    listFile.write(json.dumps(rssAll, ensure_ascii=False))
    listFile.close()
    print("====== End reptile ======")


if __name__ == "__main__":
    main()
######################################################################################
