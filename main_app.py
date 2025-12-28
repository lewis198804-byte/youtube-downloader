from pytubefix import YouTube
from flask import Flask, render_template, request, send_from_directory, url_for, jsonify
import sqlite3
import os
import threading
from datetime import timedelta , datetime


current_url = ''
save_path = "/home/lewis/Downloads/youtube_videos/"
app = Flask(__name__)
DOWNLOADS_DIR = os.path.join(app.root_path, 'downloads')
print(DOWNLOADS_DIR)
# known issues : if the same video is downloaded more than once, only one file but multiple databse entries

@app.route('/')
def index():
    con = sqlite3.connect('database.db')
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    table_check = cur.execute('SELECT name FROM sqlite_master WHERE name="videos"')
    if table_check.fetchone() is None:
        cur.execute('CREATE TABLE videos (title, video_id, channel, download_date,category,file_path,length,file_size,progress) ')
        cur.execute('CREATE TABLE bookmarks (video_id TEXT, bookmark_time REAL, name TEXT, timestamp DATETIME, PRIMARY KEY (video_id, bookmark_time))')
    else:
        cur.execute('SELECT * FROM videos ORDER BY channel ASC')
       
        res = cur.fetchall()
       
    con.close()
    return render_template('index.html', db_vids=res)



@app.route('/grab_detail', methods=['POST'])
def grab_deets():
    global current_url
    url = request.form['url']
    if url != '':
        try:
            yt = YouTube(url)
            author = (yt.author)
            vid_title = yt.title
            video_seconds = yt.length
            vid_length = timedelta(seconds=video_seconds)    
        except:
            error_tex = 'An exception occurred'
            return render_template('error.html',error_text=error_tex)

        else:
            #no excpetion and video details should be grabbed fine so pass variables
            current_url = url
            streams = yt.streams.filter(progressive=True, file_extension="mp4")
            for s in streams:
                print(s.resolution, s.mime_type)
            return render_template('video_details.html',video_author=author, 
                               video_title = vid_title,video_url=url,video_length=vid_length)
    else:
        return render_template('error.html',error_text='No url entered')

@app.route('/download', methods=['POST'])
def download_vid():
    global save_path
   
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    yt = YouTube(current_url,on_complete_callback=on_complete)
    video_seconds = yt.length
    video_length = timedelta(seconds=video_seconds)
    
    if "audio_only" in request.form:
        save_path = DOWNLOADS_DIR+"/audio/"+yt.author
        stream = yt.streams.get_audio_only()
        category = "audio"
        file_path = save_path+'/'+yt.title+'.m4a'
    else:
        save_path = DOWNLOADS_DIR+"/video/"+yt.author
        stream = yt.streams.get_highest_resolution()
        category = "video"
        file_path = save_path+'/'+yt.title+'.mp4'
    
    
    try:
        stream.download(output_path=save_path)
    except:
        return render_template('error.html',error_text='Couldn\'t download video')
    else:
        download_date = datetime.now()
        download_date = download_date.strftime('%d-%b-%y')
        file_size_bytes = os.path.getsize(file_path)
        
        if file_size_bytes < 1000000000 :
            size = str(round(file_size_bytes / (1024 * 1024))) + "MB"
        else:
            size = str(round(file_size_bytes / (1024 ** 3))) + "GB"
        
        cur.execute(
            'INSERT INTO videos (title, video_id, channel, download_date,category,file_path,length,file_size) VALUES (?,?,?,?,?,?,?,?)', 
            (yt.title,yt.video_id,yt.author,download_date,category,file_path,str(video_length),size))
        con.commit()
        con.close()
        return render_template('download.html',sucess_text='Video downloaded')

@app.route('/delete', methods=['POST'])
def delete_vid():
    if len(request.form) > 0:

        con = sqlite3.connect('database.db')
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        selected = request.form
        delete_list = []
        for video in selected:
            cur.execute('SELECT title,channel,category, file_path FROM videos WHERE video_id = ?', (video,))
            vid_ref = cur.fetchone()
            delete_list.append(vid_ref['title'])
            delete_count = len(delete_list)
            
            if os.path.exists(vid_ref['file_path']):
                os.remove(vid_ref['file_path'])
                cur.execute('DELETE FROM videos WHERE video_id = ? AND category = ?', (video,vid_ref['category']))
                con.commit()
                
                file_dir = os.path.dirname(vid_ref['file_path'])
                if len(os.listdir(file_dir)) == 0:
                    os.rmdir(file_dir)
            else:
                print("file not found: ", vid_ref['file_path'])
        con.close()
        return render_template('delete.html',number = delete_count,delete_text= delete_list)
    else:
        print('uh uh')
        return render_template('error.html',error_text='no videos selected to delete')


@app.route('/media/<path:subpath>')
def serve_media(subpath):
    return send_from_directory(DOWNLOADS_DIR, subpath)


@app.route('/player/<video_id>')
def player(video_id):
    con = sqlite3.connect('database.db')
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT file_path, title, channel, category, progress FROM videos WHERE video_id = ?", (video_id,))
    res = cur.fetchone()
    cur.execute("SELECT * FROM bookmarks WHERE video_id = ? ORDER BY bookmark_time ASC", (video_id,))
    bookmark_res = cur.fetchall()

    con.close()
    
    if not res:
        return "Video not found", 404
    
    if res['category'] == "audio":
        folder = "audio"
    else:
        folder = "video"
    if res['progress'] != "":
        video_position = res['progress']
    else:
        video_position = ""

    # Extract relative path from full path (assuming DOWNLOADS_DIR is your base)
    folder_path = os.path.join(DOWNLOADS_DIR, folder)
    print("folder path: ",folder_path)
    rel_path = os.path.relpath(res['file_path'], DOWNLOADS_DIR)
    print(rel_path)
    # Generate the URL that points to your serve_media route
    media_url = url_for('serve_media', subpath=rel_path)
    
    return render_template('player.html', 
                         media_url=media_url,
                         title=res['title'],
                         channel=res['channel'],
                         video_id = video_id,
                         video_pos = video_position,
                         bookmarks = bookmark_res)

@app.route("/save_progress/<video_id>", methods=['POST'])
def save_progress(video_id):
    data = request.get_json()
    progress = data['progress']
    print("saving_progress")
    con = sqlite3.connect('database.db')
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("UPDATE videos SET progress = ? WHERE video_id = ?", (progress, video_id))
    con.commit()
    con.close()
    return "saved"


@app.route("/save_bookmark/<video_id>", methods=['POST'])
def save_bookmark(video_id):
    data = request.get_json()
    bookmark_time = data['bookmark']
    bookmark_name = data['bookmark_name']
    vid = video_id
    print("saving_bookmark")
    con = sqlite3.connect('database.db')
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("INSERT INTO bookmarks (video_id, bookmark_time, name, timestamp) VALUES (?,?,?,?)",(vid, bookmark_time,bookmark_name, datetime.now() ))
    con.commit()
    con.close()
    return "saved bookmark"

@app.route("/delete_bookmark/<video_id>", methods=['POST'])
def delete_bookmark(video_id):
    data = request.get_json()
    bookmark_timestamp = data['timestamp']
   
    vid = video_id
    print("deleting_bookmark")
    con = sqlite3.connect('database.db')
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("DELETE FROM bookmarks WHERE video_id = ? AND timestamp = ?",(vid,bookmark_timestamp))
    con.commit()
    con.close()
    return "deleted bookmark"

@app.route("/get_bookmarks/<video_id>", methods=['GET'])
def get_bookmarks(video_id):
    con = sqlite3.connect('database.db')
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM bookmarks WHERE video_id = ? ORDER BY bookmark_time ASC", (video_id,))
    results = cur.fetchall()
    con.close()
    return jsonify([dict(row) for row in results])


def on_complete(stream, file_path):
    global current_title
    print(f"\n√ Done downloading: {file_path}")
    
  
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5000)
