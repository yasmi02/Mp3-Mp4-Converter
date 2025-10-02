from django.shortcuts import render
from django.http import JsonResponse, FileResponse, Http404
from .forms import DownloadForm
from yt_dlp import YoutubeDL
import os
import tempfile
import threading
import uuid
import mimetypes

progress_data = {}  # store progress & file path


def download_thread(url, file_format, download_id):
    temp_dir = tempfile.gettempdir()
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: progress_hook(d, download_id)]
    }

    if file_format == "mp3":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        # Fixed MP4 format for web compatibility
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]
        # Merge into single MP4 file
        ydl_opts['merge_output_format'] = 'mp4'

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            if file_format == "mp3":
                file_path = os.path.splitext(file_path)[0] + ".mp3"
            else:
                # Ensure .mp4 extension
                base = os.path.splitext(file_path)[0]
                file_path = base + ".mp4"

            progress_data[download_id]['file_path'] = file_path
            progress_data[download_id]['done'] = True
            progress_data[download_id]['error'] = None
    except Exception as e:
        progress_data[download_id]['error'] = str(e)
        progress_data[download_id]['done'] = True


def progress_hook(d, download_id):
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', d.get('total_bytes_estimate', 0))
        if total:
            progress_data[download_id]['percent'] = int(downloaded / total * 100)
    elif d['status'] == 'finished':
        progress_data[download_id]['percent'] = 100


def index(request):
    download_id = None
    form = DownloadForm()
    error = None

    if request.method == "POST":
        form = DownloadForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            file_format = form.cleaned_data['format']
            download_id = str(uuid.uuid4())
            progress_data[download_id] = {
                'percent': 0,
                'done': False,
                'file_path': None,
                'error': None
            }

            threading.Thread(target=download_thread, args=(url, file_format, download_id)).start()

    return render(request, "converter/index.html", {
        "form": form,
        "download_id": download_id,
        "error": error
    })


def progress(request, download_id):
    data = progress_data.get(download_id, {'percent': 0, 'done': False, 'error': None})
    return JsonResponse(data)


def download_file(request, download_id):
    info = progress_data.get(download_id)
    if not info or not info.get('done'):
        raise Http404("File not ready")

    if info.get('error'):
        raise Http404(f"Download error: {info['error']}")

    if not info.get('file_path'):
        raise Http404("File path not found")

    file_path = info['file_path']

    if not os.path.exists(file_path):
        raise Http404("File not found on server")

    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()

    # Set correct MIME type
    if file_ext == '.mp3':
        content_type = 'audio/mpeg'
    elif file_ext == '.mp4':
        content_type = 'video/mp4'
    else:
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
    response['Content-Type'] = content_type
    return response