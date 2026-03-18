import subprocess
import json
import tkinter as tk
from tkinter import filedialog
import os
import platform

# --- CONFIGURATION & MENUS ---
VIDEO_CODECS = {
    "1": ("H.264 (Most Compatible)", "libx264"),
    "2": ("H.265 (High Efficiency)", "libx265"),
    "3": ("VP9 (Google/WebM)", "libvpx-vp9"),
    "4": ("Copy (No Re-encoding - Fast!)", "copy")
}

AUDIO_CODECS = {
    "1": ("AAC (Standard)", "aac"),
    "2": ("MP3", "libmp3lame"),
    "3": ("OPUS (High Quality Audio)", "libopus"),
    "4": ("Copy (No Re-encoding)", "copy")
}

EXT_MAP = {
    'video': '.mp4',
    'audio': '.mp3',
    'subtitle': '.srt'
}

def clear_screen():
    """Cleans the terminal clutter based on the Operating System."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def check_dependencies():
    """Verify that FFmpeg tools are in the system PATH."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def select_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Media Source",
        filetypes=[("Media Files", "*.mkv *.mp4 *.avi *.mov *.mp3 *.wav"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path

def select_sub():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Subtitle File",
        filetypes=[("Subtitle Files", "*.srt *.ass *.vtt"), ("All Files", "*.*")]
    )
    root.destroy()
    return file_path

def get_metadata(file_path):
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

def get_destination_path(default_dir):
    """Helper to ask for destination path. Defaults to source dir if blank."""
    print(f"\n--- DESTINATION ---")
    dest = input(f"Enter destination folder path (Leave blank for source folder): ").strip()
    if not dest or not os.path.isdir(dest):
        return default_dir
    return dest

def get_selection(menu_dict, title):
    print(f"\n--- {title.upper()} SELECTION ---")
    for key, (label, _) in menu_dict.items():
        print(f" [{key}] {label}")
    
    while True:
        choice = input(f"\nSelect option (1-{len(menu_dict)}) or 'B' to go back: ").strip().upper()
        if choice == 'B':
            return "BACK"
        if choice in menu_dict:
            return menu_dict[choice][1]
        print("Invalid entry. Please try again.")

def extract_track(input_file, metadata):
    clear_screen()
    print("--- EXTRACTION ENGINE ---")
    streams = metadata.get('streams', [])
    input_dir = os.path.dirname(input_file)

    for i, s in enumerate(streams):
        codec = s.get('codec_name', 'unknown')
        lang = s.get('tags', {}).get('language', 'und')
        print(f" Stream {i:02d} | {s['codec_type'].upper():<10} | {codec:<10} | {lang}")

    choice = input("\nEnter Stream Index or 'B' to cancel: ").strip().upper()
    if choice == 'B': return

    try:
        idx = int(choice)
        selected_stream = streams[idx]
    except (ValueError, IndexError):
        print("Error: Invalid index.")
        return

    codec_name = selected_stream.get('codec_name', '')
    stream_type = selected_stream['codec_type']

    if codec_name in ['hdmv_pgs_subtitle', 'pgssub', 'dvdsub', 'dvd_subtitle']:
        req_ext = '.sup'
        print(f"NOTE: This is an IMAGE-based subtitle ({codec_name}). Using .sup extension.")
    else:
        req_ext = EXT_MAP.get(stream_type, '.mkv')

    out_name = input(f"Enter output name (Extension {req_ext} added automatically) or 'B' to cancel: ").strip()
    if out_name.upper() == 'B': return
    
    if not out_name: out_name = f"extracted_{idx}"
    if not out_name.lower().endswith(req_ext): out_name += req_ext

    target_dir = get_destination_path(input_dir)
    final_path = os.path.join(target_dir, out_name)
    
    cmd = ['ffmpeg', '-hide_banner', '-i', input_file, '-map', f'0:{idx}', '-c', 'copy', '-y', final_path]
    
    print(f"\nProcessing: {out_name}...")
    try:
        subprocess.run(cmd, check=True)
        print(f"\n[SUCCESS] File located at: {final_path}")
    except subprocess.CalledProcessError:
        print("\n[ERROR] FFmpeg failed. PGS subtitles cannot be saved as SRT.")

def add_subtitle_track(video_file):
    print("\n--- SUBTITLE MUXING ENGINE ---")
    print("Please select the Subtitle file (.srt, .ass, etc.) [Cancel by closing file dialog]")
    sub_file = select_sub()
    
    if not sub_file:
        print("No subtitle file selected. Returning to menu.")
        return

    input_dir = os.path.dirname(video_file)
    lang = input("Enter language code (e.g., eng, hin) [default: eng] or 'B' to cancel: ").strip()
    if lang.upper() == 'B': return
    if not lang: lang = "eng"

    out_name = input("Enter output filename (Default: video_with_subs.mkv) or 'B' to cancel: ").strip()
    if out_name.upper() == 'B': return
    
    if not out_name:
        out_name = "video_with_subs.mkv"
    if not out_name.lower().endswith(('.mkv', '.mp4')):
        out_name += ".mkv"

    target_dir = get_destination_path(input_dir)
    final_path = os.path.join(target_dir, out_name)

    cmd = [
        'ffmpeg', '-hide_banner', 
        '-i', video_file, 
        '-i', sub_file, 
        '-map', '0', '-map', '1', 
        '-c', 'copy', 
        f'-metadata:s:s:0', f'language={lang}', 
        '-y', final_path
    ]

    print(f"\nMuxing tracks into: {out_name}...")
    try:
        subprocess.run(cmd, check=True)
        print(f"\n[SUCCESS] New track added! Saved to: {final_path}")
    except subprocess.CalledProcessError:
        print("\n[ERROR] Muxing failed.")

def change_title(input_file, output_file, new_title):
    command = [
        'ffmpeg',
        '-y',
        '-i', input_file,
        '-map', '0',
        '-c', 'copy',
        '-metadata', f'title={new_title}',
        output_file
    ]
    
    try:
        subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0)
        print("Title updated successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")

def remove_track(input_file, metadata):
    clear_screen()
    print("--- TRACK REMOVAL ENGINE ---")
    streams = metadata.get('streams', [])
    input_dir = os.path.dirname(input_file)

    for i, s in enumerate(streams):
        codec = s.get('codec_name', 'unknown')
        lang = s.get('tags', {}).get('language', 'und')
        print(f" Stream {i:02d} | {s['codec_type'].upper():<10} | {codec:<10} | {lang}")

    choice = input("\nEnter Stream Index to REMOVE or 'B' to cancel: ").strip().upper()
    if choice == 'B': return

    try:
        idx = int(choice)
        if idx < 0 or idx >= len(streams):
            raise IndexError
    except (ValueError, IndexError):
        print("Error: Invalid stream index.")
        input("Press Enter to continue...")
        return

    original_ext = os.path.splitext(input_file)[1]
    out_name = input(f"Enter output name (Default: cleaned_file{original_ext}) or 'B' to cancel: ").strip()
    if out_name.upper() == 'B': return

    if not out_name:
        out_name = f"cleaned_file{original_ext}"
    if not out_name.lower().endswith(original_ext):
        out_name += original_ext

    target_dir = get_destination_path(input_dir)
    final_path = os.path.join(target_dir, out_name)

    cmd = [
        'ffmpeg', '-hide_banner',
        '-i', input_file,
        '-map', '0',
        f'-map', f'-0:{idx}',
        '-c', 'copy',
        '-y', final_path
    ]

    print(f"\nRemoving Stream {idx} and saving to: {out_name}...")
    try:
        subprocess.run(cmd, check=True)
        print(f"\n[SUCCESS] Track removed! Saved to: {final_path}")
    except subprocess.CalledProcessError:
        print("\n[ERROR] FFmpeg failed.")

def run_conversion(input_file):
    clear_screen()
    print("--- CONVERSION ENGINE ---")
    input_dir = os.path.dirname(input_file)
    
    v_codec = get_selection(VIDEO_CODECS, "Video Codec")
    if v_codec == "BACK": return
    
    a_codec = get_selection(AUDIO_CODECS, "Audio Codec")
    if a_codec == "BACK": return
    
    out_name = input("\nEnter target filename (e.g. final_video.mp4) or 'B' to cancel: ").strip()
    if out_name.upper() == 'B': return
    if not out_name: out_name = "converted_output.mp4"
    if not "." in out_name: out_name += ".mp4"

    target_dir = get_destination_path(input_dir)
    final_path = os.path.join(target_dir, out_name)
    
    cmd = ['ffmpeg', '-hide_banner', '-i', input_file, '-c:v', v_codec, '-c:a', a_codec, final_path]
    
    print(f"\nTranscoding: {out_name}...")
    try:
        subprocess.run(cmd, check=True)
        print(f"\n[SUCCESS] File located at: {final_path}")
    except subprocess.CalledProcessError:
        print("\n[ERROR] Conversion failed.")

def main():
    if not check_dependencies():
        print("CRITICAL ERROR: FFmpeg or FFprobe not found in system PATH.")
        return

    clear_screen()
    print("="*60)
    print("""
██████ ██████ ▄▄   ▄▄ ▄▄▄▄  ▄▄▄▄▄  ▄▄▄▄   ██     ██ ▄▄▄▄   ▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄▄▄▄ ▄▄▄▄  
██▄▄   ██▄▄   ██▀▄▀██ ██▄█▀ ██▄▄  ██ ▄▄   ██ ▄█▄ ██ ██▄█▄ ██▀██ ██▄█▀ ██▄█▀ ██▄▄  ██▄█▄ 
██     ██     ██   ██ ██    ██▄▄▄ ▀███▀    ▀██▀██▀  ██ ██ ██▀██ ██    ██    ██▄▄▄ ██ ██
    """)
    print("""
Select a media file to convert or extract streams from. 
Supported formats include MKV, MP4, AVI, MOV, MP3, WAV, and more.
    """)
    print("="*60)
    
    path = select_file()
    if not path:
        print("\nOperation cancelled by user.")
        return

    try:
        path = os.path.abspath(path)
        data = get_metadata(path)
        
        clear_screen()
        print(f"SOURCE: {os.path.basename(path)}")
        print(f"PATH  : {os.path.dirname(path)}")
        print("-" * 60)
        
        print(" [1] FULL CONVERSION (Change Format/Codecs)")
        print(" [2] STREAM EXTRACTION (Isolate Audio/Subs/Video)")
        print(" [3] ADD SUBTITLE TRACK (MUX SRT into Video)")
        print(" [4] CHANGE TITLE METADATA (No Re-encode)")
        print(" [5] REMOVE TRACK (Delete Unwanted Audio/Subs Track)")
        print(" [Q] EXIT")
        
        mode = input("\nSELECT OPERATION: ").strip().lower()
        
        if mode == "1":
            run_conversion(path)
        elif mode == "2":
            extract_track(path, data)
        elif mode == "3":
            add_subtitle_track(path)
        elif mode == "4":
            new_title = input("Enter new title or 'B' to cancel: ").strip()
            if new_title.upper() == 'B' or not new_title:
                print("Action cancelled.")
            else:
                out_name = input("Enter output filename (Default: titled_output.mkv) or 'B' to cancel: ").strip()
                if out_name.upper() != 'B':
                    if not out_name: out_name = "titled_output.mkv"
                    elif not out_name.lower().endswith(('.mkv', '.mp4')): out_name += ".mkv"
                    
                    target_dir = get_destination_path(os.path.dirname(path))
                    output_path = os.path.join(target_dir, out_name)
                    change_title(path, output_path, new_title)
        elif mode == "5":
            remove_track(path, data)
        elif mode == "q":
            print("Exiting..."); return
        else:
            print("Invalid selection.")
            
    except Exception as e:
        print(f"\n[SYSTEM ERROR] {e}")
    
    input("\nPress Enter to continue...")
    main()

if __name__ == "__main__":
    main()