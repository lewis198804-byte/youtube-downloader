from pytubefix import YouTube
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import threading
from datetime import timedelta , datetime


current_url = ''
save_path = "/home/lewis/Downloads/youtube_videos/"
app = Flask(__name__)


# known issues : if the same video is downloaded more than once, only one file but multiple databse entries

@app.route('/')
def index():
    con = sqlite3.connect('database.db')
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    table_check = cur.execute('SELECT name FROM sqlite_master WHERE name="videos"')
    if table_check.fetchone() is None:
        cur.execute('CREATE TABLE videos (title, video_id, channel, download_date,category,file_path,length) ')
    else:
        cur.execute('SELECT * FROM videos ORDER BY channel ASC')
       
        res = cur.fetchall()
        print(res)
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
        save_path = "/home/lewis/Downloads/youtube_audio/"+yt.author
        stream = yt.streams.get_audio_only()
        category = "audio"
        file_path = save_path+'/'+yt.title+'.m4a'
    else:
        save_path = "/home/lewis/Downloads/youtube_video/"+yt.author
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
        cur.execute(
            'INSERT INTO videos (title, video_id, channel, download_date,category,file_path,length) VALUES (?,?,?,?,?,?,?)', 
            (yt.title,yt.video_id,yt.author,download_date,category,file_path,str(video_length)))
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

def on_complete(stream, file_path):
    global current_title
    print(f"\n√ Done downloading: {file_path}")
    
  
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5000)
