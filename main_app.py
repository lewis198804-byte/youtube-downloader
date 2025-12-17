from pytubefix import YouTube
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import threading



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
        cur.execute('CREATE TABLE videos (title, video_id, channel, download_date) ')
    else:
        cur.execute('SELECT channel, title, download_date, video_id FROM videos')
       
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
            print(yt.length)       
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
                               video_title = vid_title,video_url=url)
    else:
        return render_template('error.html',error_text='No url entered')

@app.route('/download', methods=['POST'])
def download_vid():
    if "audio_only" in request.form:
        print("yes")
    else:
        print("no")
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    yt = YouTube(current_url,on_complete_callback=on_complete)
    stream = yt.streams.get_highest_resolution()
    
    try:
        stream.download(output_path=save_path+yt.author)
    except:
        return render_template('error.html',error_text='Couldn\'t downlaod video')
    else:
        cur.execute(
            'INSERT INTO videos (title, video_id, channel, download_date) VALUES (?,?,?,"test date")', 
            (yt.title,yt.video_id,yt.author))
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
            cur.execute('SELECT title,channel FROM videos WHERE video_id = ?', (video,))
            vid_ref = cur.fetchone()
            delete_list.append(vid_ref['title'])
            delete_count = len(delete_list)
            video_address = vid_ref['channel'] + "/"+ vid_ref['title']+".mp4"
            if os.path.exists(save_path+video_address):
                os.remove(save_path+video_address)
                if len(os.listdir(save_path+vid_ref['channel'])) == 0:
                    os.rmdir(save_path+vid_ref['channel'])

            else:
                print("file not found")
            cur.execute('DELETE FROM videos WHERE video_id = ?', (video,))
            con.commit()
        
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
