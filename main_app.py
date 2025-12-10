from pytubefix import YouTube
from flask import Flask, render_template, request, jsonify
import tkinter as tk
from tkinter import ttk
import threading

app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/grab_detail', methods=['POST'])
def download():
    data = request.json
    url = data['url']
    # Your pytubefix code here
    return jsonify({'message': f'Downloading {url}...'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5000)

root = tk.Tk()
title_text = tk.StringVar()
bytes_remaining = tk.IntVar()
bytes_left = tk.IntVar()
audio_option = tk.IntVar()

current_title = ''
root.title("Downloader")
root.geometry("500x400")

def on_progress(stream,chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    progress = int(bytes_downloaded / total_size * 100)  # percent
    bytes_left.set(bytes_remaining)
    root.after(0, progress_var.set, progress)


def grab():
    global current_title
    url = url_entry.get()
    if url != '':
        print('Grabbing Details')
        try:
            yt = YouTube(url_entry.get())
            print(yt.author)
            title_text.set(yt.title)
            current_title = yt.title
            url_entry.config(state='disabled')
            grab_button.config(state='disabled')
        except:
             print('exception happened')
        else:
            download_button.config(state='active')
    else:
         print('no url entered')
    
def start_download():
    thread = threading.Thread(target=download_vid)
    thread.daemon = True  # Allows the thread to exit when main program exits
    thread.start()

def download_vid():
    
    yt = YouTube(url_entry.get(), on_progress_callback=on_progress,on_complete_callback=on_complete)
    
    if audio_option.get() == 0:
        stream = yt.streams.get_highest_resolution()
        save_path = "/home/lewis/Downloads/youtube_videos/"
    else:
        stream = yt.streams.get_audio_only()
        save_path = "/home/lewis/Downloads/youtube_audio/"

    stream.download(output_path=save_path+yt.author)
    url_entry.delete(0,len(url_entry.get()))


def on_complete(stream, file_path):
    global current_title
    print(f"\n√ Done downloading: {file_path}")
    insert_index = completed_downloads.size() + 1
    if audio_option.get() == 0:
        download_type = 'Video'
    else:
        download_type = 'Audio'
    completed_downloads.insert(insert_index,current_title+ ' - '+ download_type)
    current_title = ''
    title_text.set('')
    download_button.config(state='disabled')
    url_entry.config(state='normal')
    grab_button.config(state='active')
    progress_var.set(0)

def start_over():
    global current_title
    url_entry.config(state='normal')
    entry_length = len(url_entry.get())
    url_entry.delete(0,entry_length)
    current_title = ''
    grab_button.config(state='active')
    download_button.config(state='disabled')
    title_text.set('')
    

url_label = tk.Label(root,text='Video URL',pady=20)
url_entry = tk.Entry(root)
grab_button = tk.Button(root,text='Grab Video',command=grab)
clear_button = tk.Button(root,text='Start over', command=start_over)
video_title = tk.Label(root,textvariable=title_text)
download_button = tk.Button(root,text='Download',command=start_download,state='disabled')
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(root, length=300, variable=progress_var, maximum=100)
completed_downloads = tk.Listbox(root,width=300)
bytes_left_label = tk.Label(textvariable=bytes_left)
audio_checkbutton = tk.Checkbutton(root,text='Audio only?',variable=audio_option,onvalue=1,offvalue=0)
url_label.pack()
url_entry.pack()
grab_button.pack()
video_title.pack()
download_button.pack()
audio_checkbutton.pack()
clear_button.pack()
progress_bar.pack(pady=10)
bytes_left_label.pack()
completed_downloads.pack()


root.mainloop()