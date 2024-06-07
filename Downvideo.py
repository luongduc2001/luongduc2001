import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import yt_dlp
import threading
import subprocess
import json

def download_content(url, output_path, format_type, progress_callback):
    download_path = os.path.join(output_path, '%(title)s.%(ext)s')
    ydl_opts = {
        'outtmpl': download_path,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'progress_hooks': [lambda d: progress_callback(d, url)],
        'merge_output_format': 'mp4',
    }
    if format_type == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif format_type == 'mp4':
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4'
    else:
        raise ValueError("Invalid format")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if format_type == 'mp4':
        downloaded_file = get_downloaded_filename(download_path, url, ydl)
        if not is_supported_codec(downloaded_file):
            converted_file = downloaded_file.replace('.mp4', '_converted.mp4')
            reset_progress_bar()
            convert_to_h264(downloaded_file, converted_file, progress_callback, url)
        else:
            messagebox.showinfo("Info", "The downloaded file has a supported codec.")

def get_downloaded_filename(template, url, ydl):
    info_dict = ydl.extract_info(url, download=False)
    filename = ydl.prepare_filename(info_dict)
    base, ext = os.path.splitext(filename)
    ext = ext[1:]  # Remove the leading dot
    return template % {'title': info_dict['title'], 'ext': ext}

def is_supported_codec(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name', '-of', 'json', file_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        streams = json.loads(result.stdout)['streams']
        supported_video_codec = 'h264'
        supported_audio_codec = 'aac'
        
        video_codec_supported = any(stream['codec_name'] == supported_video_codec for stream in streams if stream['codec_type'] == 'video')
        audio_codec_supported = any(stream['codec_name'] == supported_audio_codec for stream in streams if stream['codec_type'] == 'audio')
        
        return video_codec_supported and audio_codec_supported
    except Exception as e:
        print(f"Error checking codec: {e}")
        return False

def convert_to_h264(input_file, output_file, progress_callback, url):
    command = [
        'ffmpeg', '-y', '-i', input_file, '-c:v', 'h264_nvenc', '-c:a', 'aac', '-strict', 'experimental', output_file
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')

    total_frames = get_total_frames(input_file)
    for line in iter(process.stdout.readline, ''):
        if 'frame=' in line:
            frame_match = re.search(r'frame=\s*(\d+)', line)
            if frame_match:
                frame = int(frame_match.group(1))
                progress = (frame / total_frames) * 100
                progress_callback({'status': 'converting', 'progress': progress}, url)
    
    process.wait()
    os.remove(input_file)
    messagebox.showinfo("Success", "Conversion completed!")

def get_total_frames(input_file):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries', 'stream=nb_read_frames', '-of', 'json', input_file],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    frames_info = json.loads(result.stdout)
    total_frames = int(frames_info['streams'][0]['nb_read_frames'])
    return total_frames

def paste_link():
    try:
        url = root.clipboard_get()
        url_entry.delete(0, tk.END)
        url_entry.insert(0, url)
    except tk.TclError:
        messagebox.showerror("Error", "No link found in clipboard.")

def browse_folder():
    folder_selected = filedialog.askdirectory()
    folder_path.set(folder_selected)

def start_download():
    url = url_entry.get().strip()
    output_folder = folder_path.get().strip()
    format_type = format_choice.get()

    if not url:
        messagebox.showerror("Error", "Please enter a URL.")
        return

    if not output_folder:
        messagebox.showerror("Error", "Please select an output folder.")
        return

    canvas.coords(progress_bar, 0, 0, 0, 20)
    threading.Thread(target=download_content, args=(url, output_folder, format_type, progress_hook), daemon=True).start()

def progress_hook(d, url):
    if d['status'] == 'downloading':
        percent_match = re.search(r'(\d+\.\d+)%', d['_percent_str'])
        if percent_match:
            percent = float(percent_match.group(1))
            update_progress(percent)
    elif d['status'] == 'converting':
        percent = d['progress']
        update_progress(percent)
    elif d['status'] == 'finished':
        update_progress(100)
        messagebox.showinfo("Success", "Download completed!")

def reset_progress_bar():
    canvas.coords(progress_bar, 0, 0, 0, 20)
    canvas.itemconfig(progress_bar, fill="green")

def update_progress(percent):
    width = int(percent * 3)
    canvas.coords(progress_bar, 0, 0, width, 20)

root = tk.Tk()
root.title("TikTok Downloader")

url_label = tk.Label(root, text="Enter TikTok video URL:")
url_label.pack(pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)
paste_button = tk.Button(root, text="Paste link", command=paste_link)
paste_button.pack(pady=5)

folder_label = tk.Label(root, text="Select output folder:")
folder_label.pack(pady=5)
folder_path = tk.StringVar()
folder_entry = tk.Entry(root, textvariable=folder_path, width=50)
folder_entry.pack(pady=5)
browse_button = tk.Button(root, text="Browse", command=browse_folder)
browse_button.pack(pady=5)

format_label = tk.Label(root, text="Select format:")
format_label.pack(pady=5)

format_choice = tk.StringVar()
format_choice.set("mp4")

mp4_radio = tk.Radiobutton(root, text="MP4", variable=format_choice, value="mp4")
mp4_radio.pack(pady=5)

mp3_radio = tk.Radiobutton(root, text="MP3", variable=format_choice, value="mp3")
mp3_radio.pack(pady=5)

download_button = tk.Button(root, text="Download", command=start_download)
download_button.pack(pady=10)

progress_frame = tk.Frame(root)
progress_frame.pack(pady=10)

canvas = tk.Canvas(progress_frame, width=300, height=20, bg="lightgray")
canvas.pack()

progress_bar = canvas.create_rectangle(0, 0, 0, 20, fill="green")

root.mainloop()
