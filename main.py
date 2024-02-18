import glob
import hashlib
import os
import random
import re
from datetime import datetime
from threading import Thread
import pytz
from flask import Flask, redirect, request, send_file, url_for, render_template
from flask_socketio import SocketIO
import json

ninnin = json.load(open("ninja.json","r",encoding="utf-8"))

emoji_pattern = re.compile(
    "["
    u"\U0001F600-\U0001F64F"  # スマイル絵文字
    u"\U0001F300-\U0001F5FF"  # シンボル
    u"\U0001F680-\U0001F6FF"  # 車や建物
    u"\U0001F700-\U0001F77F"  # 音符
    u"\U0001F780-\U0001F7FF"  # フラッグ
    u"\U0001F800-\U0001F8FF"  # その他
    u"\U0001F900-\U0001F9FF"  # 顔
    u"\U0001FA00-\U0001FA6F"  # スポーツ
    u"\U0001FA70-\U0001FAFF"  # 食べ物
    u"\U0001F004-\U0001F0CF"  # 追加の絵文字
    u"\U0001F200-\U0001F251"  # 装飾記号
    "]+",
    flags=re.UNICODE)
# テキストからURLを検出する正規表現パターン
url_pattern = r'(https?://\S+)'
counter = 0
pv = {}

def count(path):
  a = str(int(open(path, "r").read()) + 1)
  open(path, "w", encoding="utf-8").write(a)
  return open(path, "r",encoding="utf-8").read()


def get_japantime():
  japan_tz = pytz.timezone('Asia/Tokyo')
  return str(datetime.now(japan_tz)).replace("+09:00", "")


app = Flask(__name__)
skio = SocketIO(app)


@app.route('/')
def index():
  return render_template('index.html').replace("<!-- News -->",open("news.html","r",encoding="UTF-8").read())


@app.route("/bbs/<bbs>")
def bbspage(bbs):
  hoge = ""
  p = glob.glob(f"bbs/{bbs}/*/")
  for i in p:
    print(i)
    url = i.replace(f"bbs/{bbs}\\", "").replace("/", "")
    try:
      threadtitle = open(f"{i}title.txt", "r",encoding="utf-8").read()
      threadcount = open(f"{i}count.txt", "r",encoding="utf-8").read()
      hoge += f"<a href=\"/test/read.cgi/{bbs}/{url}/\">{threadtitle}({threadcount})</a><br>\n"
    except FileNotFoundError:
      pass
  if len(p) == 0:
    hoge = "<p style='text-align:center'>ないみたい</p>"
  return render_template(
      "bbs.html",
      bbsname=open(f"bbs/{bbs}/title.txt", "r",encoding="utf-8").read(),
      bbsdesc=open(f"bbs/{bbs}/description.txt", "r",encoding="utf-8").read(),
      bbsid=bbs,
  ).replace("<!-- bbsthread -->", hoge)


@app.route('/test/read.cgi/<bbs>/<thread>/')
def display_thread_with_views(bbs, thread):
  # スレッドのキーを作成
  key = f'{bbs}/{thread}'
  with open(f"bbs/{bbs}/{thread}/title.txt", "r",encoding="utf-8") as title_file:
    thread_title = title_file.read()

  # スレッドの投稿内容をファイルから読み込み、整形する
  formatted_messages = format_thread_messages(bbs, thread)

  # スレッドの表示用HTMLをレンダリングする
  thread_html = render_template(
      'bbs_thread.html',
      threadtitle=thread_title,
      bbs=bbs,
      thread=thread,
      messages=formatted_messages,
  ).replace("<!-- message -->", formatted_messages)

  return thread_html


def format_thread_messages(bbs, thread):
  # スレッドの投稿内容をファイルから読み込む
  with open(f"bbs/{bbs}/{thread}/dat.txt", "r",encoding="utf-8") as dat_file:
    messages = dat_file.read()

  # リンクと引用を整形する
  formatted_messages = re.sub(
      r"＞＞([0-9]+)",
      r"<a href='/test/read.cgi/" + bbs + "/" + thread + r"/\1'>＞＞\1</a>",
      re.sub(url_pattern,
             r"<a href='\1' target='_blank' rel='noopener noreferrer'>\1</a>",
             messages))

  return formatted_messages



@app.route('/test/read.cgi/<bbs>/<thread>/<num>')
def display_thread_anker(bbs, thread, num):
  # ファイルからスレッドのタイトルを読み込む
  with open(f"bbs/{bbs}/{thread}/title.txt", "r",encoding="utf-8") as title_file:
    thread_title = title_file.read()

  # ファイルからスレッドの投稿内容を読み込む
  with open(f"bbs/{bbs}/{thread}/dat.txt", "r",encoding="utf-8") as dat_file:
    messages = dat_file.read().split("\n")

  # スレッドの投稿内容をHTML形式に整形する
  formatted_messages = format_messages(messages, bbs, thread)

  # スレッドの表示用HTMLをレンダリングする
  thread_html = render_template(
      'bbs_thread.html',
      threadtitle=thread_title,
      bbs=bbs,
      thread=thread,
  )
  if num.isdecimal():
    return thread_html.replace("<!-- message -->", formatted_messages[int(num)-1])
  elif num == "l10":
    return thread_html.replace("<!-- message -->", "".join(formatted_messages[len(formatted_messages)-10:len(formatted_messages)])).replace("<!-- All_Button -->", f"　<a href='/test/read.cgi/{bbs}/{thread}/'>全部</a>")

def format_messages(messages, bbs, thread):
  formatted_messages = []

  # メッセージの投稿内容を整形する
  for message in messages:
    formatted_message = format_links_and_quotes(message, bbs, thread)
    formatted_messages.append(formatted_message)

  return formatted_messages


def format_links_and_quotes(message, bbs, thread):
  # リンクの整形
  message_with_links = re.sub(
      url_pattern,
      r"<a href='\1' target='_blank' rel='noopener noreferrer'>\1</a>",
      message)
  

  # 引用の整形
  formatted_message = re.sub(
      r"＞＞([0-9]+)", rf"<a href='/test/read.cgi/{bbs}/{thread}/\1'>＞＞\1</a>",
      message_with_links)

  return formatted_message


@skio.on("post")
def handle_post(data):
  username = data["name"].replace("<", "＜").replace(">",
                                                    "＞").replace("\n", "\n　　")
  message = data['msg'].replace("<", "＜").replace(">",
                                                  "＞").replace("\n", "<br>　　")
  mails = data["mail"].split(" ")
  nusi = False
  ua = request.headers.get('User-Agent')
  kisyu = detect_device(ua)
  browser = detect_browser(ua)
  ids = hashlib.md5(request.remote_addr.encode()).hexdigest()+f"-{kisyu}{browser}"
  if not ids in list(ninnin.keys()):
    ninnin[ids] = 0
  ninnin[ids] += 1
  if username == "":
    username = "名無しさん"
  if "ninja" in mails:
    username+=f"<font color='red'>Lv{ninnin[ids]}</font>"
  if "ryokin" in mails:
    username+=f"【<font color='blue'>利用料金は{ninnin[ids]*112}円です。</font>】"
  color = "green"
  if "kintama" in mails:
    color = "yellow"
    username.replace("!kintama", "", 1)
  if len(re.findall(r"[ぁ-ンー0-9a-zA-Z一-鿿ｱ-ﾝ]+", message)) > 0 and ninnin[ids] > 0:  #ここで空白文字を規制する
    c = count(f"bbs/{data['bbs']}/{data['threads']}/count.txt")
    open(f"bbs/{data['bbs']}/{data['threads']}/dat.txt", "a",encoding="utf-8").write(
          f"""<a onclick="addanker({c})">{c}</a>:名前: <b><font color='{color}'>{username}</font></b> {get_japantime()} ID:{ids}<br>　　{message}<br><br>\n"""
      )
    skio.emit(
        f"get-{data['bbs']}-{data['threads']}",
        re.sub(
            r"＞＞([0-9]*)", r"<a href='/test/read.cgi/" + data['bbs'] + "/" +
            data['threads'] + r"/\1'>＞＞\1</a>",
            re.sub(
                url_pattern, r"<a href='\1'>\1</a>",
                open(f"bbs/{data['bbs']}/{data['threads']}/dat.txt",
                     "r",encoding="utf-8").read())))
  json.dump(ninnin,open("ninja.json","w",encoding="utf-8"),ensure_ascii=False)


@app.route('/post_register/<bbs>/', methods=['POST'])
def post2_message(bbs):

  thread = "".join([
      random.choice(
          "1234567890aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ")
      for i in range(32)
  ])
  os.mkdir(f"bbs/{bbs}/{thread}/")
  username = request.form['username'].replace("<", "＜").replace(">", "＞")
  ua = request.headers.get('User-Agent')
  kisyu = detect_device(ua)
  browser = detect_browser(ua)
  ids = hashlib.md5(request.remote_addr.encode()).hexdigest()+f"-{kisyu}{browser}"
  mails = request.form['mail']
  if not ids in list(ninnin.keys()):
    ninnin[ids] = 0
  ninnin[ids] += 1
  if username == "":
    username = "名無しさん"
  color = "green"
  if "!kintama" in username:
    color = "yellow"
    username.replace("!kintama", "", 1)
  username.replace("★", "☆")
  if ninnin[ids]>0:
    title = request.form['title'].replace("<",
                                          "＜").replace(">",
                                                      "＞").replace("\n", "")

    message = request.form['message'].replace("<",
                                              "＜").replace(">", "＞").replace(
                                                  "\n", "<br>　　")
    open(f"bbs/{bbs}/{thread}/dat.txt", "a",encoding="utf-8").write(
        f"""<a onclick="addanker(1)">1</a>:名前: <b><font color='{color}'>{username}</font></b> {get_japantime()} ID:{ids}<br>　　{message}<br><br>\n"""
    )
    open(f"bbs/{bbs}/{thread}/title.txt", "w",encoding="utf-8").write(title)
    open(f"bbs/{bbs}/{thread}/count.txt", "w",encoding="utf-8").write("1")

  return redirect(f"/test/read.cgi/{bbs}/{thread}/")


@skio.on('connect')
def handle_connects():
  global counter
  counter += 1
  skio.emit('update_counter', {'count': counter})


@skio.on('disconnect')
def handle_disconnects():
  global counter
  counter -= 1
  skio.emit('update_counter', {'count': counter})


@app.route("/bbslist.htm")
def bbslist():
  r = ""
  for i in glob.glob("bbs/*"):
    url = i.replace("bbs\\", "")
    title = open(f"{i}/title.txt", "r",encoding="utf-8")
    r += f"<a href=\"bbs/{url}\">{title.read()}</a><br>\n"
  return render_template("bbslist.html").replace("<!-- r -->", r)


@app.route("/<bbs>/dat/<fname>")
def robots(bbs, fname):
  kak = fname.split(".")[1]
  fname = fname.split(".")[0]
  if kak == "dat":
    return send_file(f"bbs/{bbs}/{fname}/dat.txt")
  elif kak == "ttl":
    return send_file(f"bbs/{bbs}/{fname}/title.txt")
  elif kak == "cnt":
    return send_file(f"bbs/{bbs}/{fname}/count.txt")
  else:
    return "?"


@app.route('/bbsmake/', methods=['POST'])
def gadai():
  bbs = request.form['name'].replace("<", "＜").replace(">", "＞")
  bbsid = request.form['id'].replace("<", "＜").replace(">", "＞")
  desc = request.form['desc'].replace("<", "＜").replace(">", "＞")
  if not os.path.exists(f"bbs/{bbsid}/"):
    os.mkdir(f"bbs/{bbsid}/")
    open(f"bbs/{bbsid}/title.txt", "w",encoding="utf-8").write(bbs)
    open(f"bbs/{bbsid}/description.txt", "w",encoding="utf-8").write(desc)
    return redirect(f"/bbs/{bbsid}")
  else:
    return "もうその掲示板は存在するみたい。"

@app.route("/robots.txt")
def robotstxt():
  return """User-agent: *
Disallow: /bbslist.htm
Disallow
Allow: /test/read.cgi/
"""

@app.route("/Server/RemoteHost/")
def remotehost_check():
  return f"""<h1>REMOTE HOST</h1>
RemoteAddr:{request.remote_addr}<br>
RemoteUser:{request.remote_user}<br>
Date:{request.date}<br>
ContentType:{request.content_type}<br>
Referrer:{request.referrer}"""

def detect_device(user_agent):
    # ユーザーエージェントからデバイスを判別するロジックを実装
    if 'Mobile' in user_agent:
        return 'M'
    elif 'Tablet' in user_agent:
        return 'T'
    else:
        return 'D'

def detect_browser(user_agent):
    # ユーザーエージェントからブラウザを判別するロジックを実装
    if 'Firefox' in user_agent:
        return 'F'
    elif 'Chrome' in user_agent:
        return 'C'
    elif 'Safari' in user_agent:
        return 'S'
    else:
        return 'E'

@app.route("/guide.txt")
def guide():
  return send_file("Guide.txt")

if __name__ == '__main__':
  skio.run(app, "::", port=80, debug=True, allow_unsafe_werkzeug=True)
