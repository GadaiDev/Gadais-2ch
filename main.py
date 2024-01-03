import hashlib
from flask import Flask, render_template, request, redirect, url_for, send_file
import random
import glob
import os
from datetime import datetime
import pytz
from threading import Thread
import time
from flask_socketio import SocketIO
import re
# テキストからURLを検出する正規表現パターン
url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
counter = 3


def deletethreads(bbs, threads):
  time.sleep(5)
  os.rmdir(f"bbs/{bbs}/{threads}")


def count(path):
  a = str(int(open(path, "r").read()) + 1)
  open(path, "w").write(a)
  return open(path, "r").read()


def get_japantime():
  japan_tz = pytz.timezone('Asia/Tokyo')
  return datetime.now(japan_tz)


app = Flask(__name__)
skio = SocketIO(app)


@app.route('/')
def index():
  return render_template('index.html')


@app.route("/bbs/<bbs>")
def bbspage(bbs):
  hoge = ""
  p = glob.glob(f"bbs/{bbs}/*/")
  for i in p:
    url = i.replace(f"bbs/{bbs}/", "").replace(f"/", "")
    threadtitle = open(f"{i}title.txt", "r").read()
    hoge += f"<a href=\"/test/read.cgi/{bbs}/{url}/\">{threadtitle}</a><br>\n"
  if len(p) == 0:
    hoge = "<p style='text-align:center'>ないみたい</p>"
  return render_template(
      "bbs.html",
      bbsname=open(f"bbs/{bbs}/title.txt", "r").read(),
      bbsdesc=open(f"bbs/{bbs}/description.txt", "r").read(),
      bbsid=bbs,
  ).replace("<!-- bbsthread -->", hoge)


@app.route('/test/read.cgi/<bbs>/<thread>/')
def page(bbs, thread):
  return re.sub(
      r"＞＞([0-9]*)",
      r"<a href='/test/read.cgi/" + bbs + "/" + thread + r"/\1'>＞＞\1</a>",
      render_template(
          'bbs_thread.html',
          threadtitle=open(f"bbs/{bbs}/{thread}/title.txt", "r").read(),
          bbs=bbs,
          thread=thread,
      ).replace(
          "<!-- messages -->",
          open(f"bbs/{bbs}/{thread}/dat.txt",
               "r").read().replace("\n", "<br>\n")))


@app.route('/test/read.cgi/<bbs>/<thread>/<num>')
def page2(bbs, thread, num):
  return re.sub(
      r"＞＞([0-9]*)",
      r"<a href='/test/read.cgi/" + bbs + "/" + thread + r"/'>＞＞\1</a>",
      render_template(
          'bbs_thread.html',
          threadtitle=open(f"bbs/{bbs}/{thread}/title.txt", "r").read(),
          bbs=bbs,
          thread=thread,
      ).replace(
          "<!-- messages -->",
          open(f"bbs/{bbs}/{thread}/dat.txt",
               "r").read().split("\n\n")[int(num) - 1].replace("\n",
                                                               "<br>\n")))


@skio.on("post")
def handle_post(data):
  username = data["name"]
  message = data['msg'].replace("<", "＜").replace(">",
                                                  "＞").replace("\n", "\n　　")
  if data["id"] == "":
    ids = "とくさん"
  else:
    ids = "".join(list(hashlib.md5(data["id"].encode()).hexdigest())[0:12])
  if username == "":
    username = "名無しさん"
  c = count(f"bbs/{data['bbs']}/{data['threads']}/count.txt")
  open(f"bbs/{data['bbs']}/{data['threads']}/dat.txt", "a").write(
      f"""{c}:名前: <b><font color='green'>{username}</font></b> {get_japantime()} ID:{ids}
　　{message}\n\n""")
  skio.emit(
      f"get-{data['bbs']}-{data['threads']}",
      open(f"bbs/{data['bbs']}/{data['threads']}/dat.txt",
           "r").read().replace("\n", "<br>\n"))


@skio.on("rep")
def handle2_post(data):
  open("tuho.txt", "a").write(f"""通報がありました:{data["title"]}
{data["description"]}\n\n\n""")


@app.route('/post_register/<bbs>/', methods=['POST'])
def post2_message(bbs):
  thread = "".join([
      random.choice(
          "1234567890aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ")
      for i in range(32)
  ])
  os.mkdir(f"bbs/{bbs}/{thread}/")
  username = request.form['username'].replace("<", "＜").replace(">", "＞")
  if request.form["ids"] == "":
    ids = "とくさん"
  else:
    ids = "".join(
        list(hashlib.md5(request.form["ids"].encode()).hexdigest())[0:12])
  if username == "":
    username = "名無しさん"

  username.replace("★", "☆")
  title = request.form['title'].replace("<",
                                        "＜").replace(">",
                                                     "＞").replace("\n", "")

  message = request.form['message'].replace("<", "＜").replace(">",
                                                              "＞").replace(
                                                                  "\n", "\n　　")
  open(f"bbs/{bbs}/{thread}/dat.txt", "a").write(
      f"""1:名前: <b><font color='green'>{username}</font></b> {get_japantime()} ID:{ids}
　　{message}\n\n""")
  open(f"bbs/{bbs}/{thread}/title.txt", "w").write(title)
  open(f"bbs/{bbs}/{thread}/count.txt", "w").write("1")
  Thread(target=lambda: (deletethreads(bbs, thread))).start()

  return redirect(url_for('page', bbs=bbs, thread=thread))


@skio.on('connect')
def handle_connects():
  global counter
  counter += 1
  skio.emit(f'update_counter', {'count': counter})


@skio.on('disconnect')
def handle_disconnects():
  global counter
  counter -= 1
  skio.emit(f'update_counter', {'count': counter})


@app.route("/bbslist.htm")
def bbslist():
  r = ""
  for i in glob.glob("bbs/*"):
    url = i.replace("bbs/", "")
    r += f"<a href=\"bbs/{url}\">{i}</a><br>\n"
  return render_template("bbslist.html").replace("<!-- r -->", r)


@app.route("/<bbs>/dat/<fname>")
def robots(bbs, fname):
  fname = fname.split(".")[0]
  return send_file(f"bbs/{bbs}/{fname}/dat.txt")


@app.route('/bbsmake/', methods=['POST'])
def gadai():
  bbs = request.form['name'].replace("<", "＜").replace(">", "＞")
  bbsid = request.form['id'].replace("<", "＜").replace(">", "＞")
  desc = request.form['desc'].replace("<", "＜").replace(">", "＞")
  if not os.path.exists(f"bbs/{bbsid}/"):
    os.mkdir(f"bbs/{bbsid}/")
    open(f"bbs/{bbsid}/title.txt", "w").write(bbs)
    open(f"bbs/{bbsid}/description.txt", "w").write(desc)
    return redirect(f"/bbs/{bbsid}")
  else:
    return "もうその掲示板は存在するみたいやね"


@app.route("/reports")
def repview():
  return send_file("tuho.txt")


if __name__ == '__main__':
  skio.run(app, "0.0.0.0", port=8000, debug=True)
