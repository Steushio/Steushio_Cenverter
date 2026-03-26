import os
import sys
import threading
import subprocess
import re
from datetime import timedelta
import customtkinter as ctk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

# Add local ffmpeg bin to PATH so the app doesn't require a system-wide install
ffmpeg_path = os.path.join(get_resource_path("ffmpeg"), "bin")
os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")

class TkDnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FFmpegStudio(TkDnDCTk):
    def __init__(self):
        super().__init__()
        self.title("Sconvert")
        self.geometry("900x750")
        
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        self.queue = []
        self.current_process = None
        self.is_converting = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        # UI Layout: LEFT COLUMN (Settings), RIGHT COLUMN (Queue & Logs)
        left_panel = ctk.CTkFrame(main_frame, width=300)
        left_panel.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=10, pady=10)
        
        right_panel = ctk.CTkFrame(main_frame)
        right_panel.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=10)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        # =============== LEFT PANEL (SETTINGS) ===============
        ctk.CTkLabel(left_panel, text="Mode Select", font=("Inter", 16, "bold")).pack(pady=(15,5), padx=10, anchor="w")
        self.mode_var = ctk.StringVar(value="Full Re-encode")
        modes = ["Extract Audio", "Fix for Editing", "Remux", "Full Re-encode", "Compress", "OBS Fix", "YouTube", "Audio Only"]
        ctk.CTkOptionMenu(left_panel, variable=self.mode_var, values=modes).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(left_panel, text="Output Video Format", font=("Inter", 14, "bold")).pack(pady=(15,5), padx=10, anchor="w")
        self.vformat_var = ctk.StringVar(value="mp4")
        ctk.CTkOptionMenu(left_panel, variable=self.vformat_var, values=["mp4", "mkv", "mov", "avi", "webm", "Same as Input"]).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(left_panel, text="Output Audio Format", font=("Inter", 14, "bold")).pack(pady=(15,5), padx=10, anchor="w")
        self.aformat_var = ctk.StringVar(value="wav")
        ctk.CTkOptionMenu(left_panel, variable=self.aformat_var, values=["wav", "mp3", "aac", "m4a", "flac"]).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(left_panel, text="Smart Toggles", font=("Inter", 14, "bold")).pack(pady=(15,5), padx=10, anchor="w")
        self.fix_ts_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(left_panel, text="Fix timestamps (+genpts)", variable=self.fix_ts_var).pack(pady=5, padx=10, anchor="w")
        self.fix_sync_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(left_panel, text="Fix sync/VFR (-vsync 1)", variable=self.fix_sync_var).pack(pady=5, padx=10, anchor="w")
        self.uncomp_aud_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(left_panel, text="Uncompressed audio (pcm)", variable=self.uncomp_aud_var).pack(pady=5, padx=10, anchor="w")
        
        ctk.CTkLabel(left_panel, text="Audio/Video Encoding", font=("Inter", 14, "bold")).pack(pady=(15,5), padx=10, anchor="w")
        audio_frame = ctk.CTkFrame(left_panel)
        audio_frame.pack(fill="x", padx=10, pady=5)
        self.ar_var = ctk.StringVar(value="48000")
        ctk.CTkOptionMenu(audio_frame, variable=self.ar_var, values=["44100", "48000"]).pack(side="left", padx=5, pady=5)
        self.br_var = ctk.StringVar(value="192k")
        ctk.CTkOptionMenu(audio_frame, variable=self.br_var, values=["128k", "192k", "320k"]).pack(side="left", padx=5, pady=5)

        video_frame = ctk.CTkFrame(left_panel)
        video_frame.pack(fill="x", padx=10, pady=5)
        self.crf_var = ctk.StringVar(value="18")
        ctk.CTkOptionMenu(video_frame, variable=self.crf_var, values=["18", "23", "28"]).pack(side="left", padx=5, pady=5)

        # =============== RIGHT PANEL (QUEUE & LOGS) ===============
        queue_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        queue_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        ctk.CTkLabel(queue_header, text="Queue (Drag & Drop Files Here)", font=("Inter", 16, "bold")).pack(side="left")
        
        ctk.CTkButton(queue_header, text="Add Files", width=100, command=self.add_files).pack(side="right", padx=5)
        ctk.CTkButton(queue_header, text="Clear", width=80, fg_color="red", hover_color="darkred", command=self.clear_queue).pack(side="right", padx=5)

        self.queue_listbox = ctk.CTkTextbox(right_panel, height=150, font=("Consolas", 12))
        self.queue_listbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.queue_listbox.configure(state="disabled")
        
        # DND
        self.queue_listbox.drop_target_register(DND_FILES)
        self.queue_listbox.dnd_bind('<<Drop>>', self.drop_files)

        self.prog_label = ctk.CTkLabel(right_panel, text="Progress: 0%", font=("Inter", 12))
        self.prog_label.grid(row=2, column=0, sticky="w", padx=10)

        self.progress_bar = ctk.CTkProgressBar(right_panel)
        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(0,10))
        self.progress_bar.set(0)

        self.log_box = ctk.CTkTextbox(right_panel, height=180, font=("Consolas", 11), fg_color="#0D1117", text_color="#A5D6FF")
        self.log_box.grid(row=4, column=0, sticky="nsew", padx=10, pady=10)

        self.convert_btn = ctk.CTkButton(right_panel, text="START BATCH CONVERSION", font=("Inter", 18, "bold"), height=50, fg_color="#238636", hover_color="#2ea043", command=self.start_batch)
        self.convert_btn.grid(row=5, column=0, sticky="ew", padx=10, pady=10)

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def update_queue_ui(self):
        self.queue_listbox.configure(state="normal")
        self.queue_listbox.delete("1.0", "end")
        for i, f in enumerate(self.queue):
            self.queue_listbox.insert("end", f"{i+1}. {os.path.basename(f)}\n")
        self.queue_listbox.configure(state="disabled")

    def drop_files(self, event):
        files = self.tk.splitlist(event.data)
        for f in files:
            if os.path.isfile(f) and f not in self.queue:
                self.queue.append(f)
        self.update_queue_ui()
        self.log(f"Added {len(files)} files to queue.")

    def add_files(self):
        files = filedialog.askopenfilenames(title="Select Media Files")
        added = 0
        for f in files:
            if f not in self.queue:
                self.queue.append(f)
                added += 1
        self.update_queue_ui()
        if added > 0:
            self.log(f"Added {added} files to queue.")

    def clear_queue(self):
        self.queue = []
        self.update_queue_ui()
        self.log("Queue cleared.")

    def build_command(self, input_file):
        mode = self.mode_var.get()
        base, ext = os.path.splitext(input_file)
        
        # Use python explicitly if we're dealing with ffmpeg binary path
        ffmpeg_exe = os.path.join(get_resource_path("ffmpeg"), "bin", "ffmpeg.exe") if not getattr(sys, 'frozen', False) else get_resource_path("ffmpeg.exe")
        cmd = [ffmpeg_exe, "-y", "-i", input_file]

        # Toggles
        if self.fix_ts_var.get() or mode in ["Fix for Editing", "OBS Fix"]:
            cmd.extend(["-fflags", "+genpts"])
        if self.fix_sync_var.get():
            cmd.extend(["-vsync", "1"])
            
        ar = self.ar_var.get()
        br = self.br_var.get()
        crf = self.crf_var.get()
        
        out_vfmt = self.vformat_var.get()
        if out_vfmt == "Same as Input":
            out_vfmt = ext.replace(".", "")

        out_afmt = self.aformat_var.get()
        
        # Mode Logic
        if mode in ["Extract Audio", "Audio Only"]:
            out_file = f"{base}_audio.{out_afmt}"
            if out_afmt == "wav" or self.uncomp_aud_var.get():
                cmd.extend(["-vn", "-acodec", "pcm_s16le", "-ar", ar])
            elif out_afmt in ["mp3"]:
                cmd.extend(["-vn", "-acodec", "libmp3lame", "-b:a", br, "-ar", ar])
            else:
                cmd.extend(["-vn", "-c:a", "aac", "-b:a", br])
                
        elif mode == "Fix for Editing":
            out_file = f"{base}_edit.{out_vfmt}"
            cmd.extend(["-c:v", "copy", "-c:a", "pcm_s16le", "-ar", ar])
            
        elif mode == "Remux":
            out_file = f"{base}_remux.{out_vfmt}"
            cmd.extend(["-c", "copy"])
            
        elif mode in ["Full Re-encode", "OBS Fix", "YouTube"]:
            out_file = f"{base}_reencode.{out_vfmt}"
            cmd.extend(["-c:v", "libx264", "-crf", crf, "-preset", "fast"])
            if self.uncomp_aud_var.get():
                cmd.extend(["-c:a", "pcm_s16le", "-ar", ar])
            else:
                cmd.extend(["-c:a", "aac", "-b:a", br, "-ar", ar])
                
        elif mode == "Compress":
            out_file = f"{base}_compress.{out_vfmt}"
            cmd.extend(["-c:v", "libx264", "-crf", "28", "-preset", "fast", "-c:a", "aac", "-b:a", "128k"])

        cmd.append(out_file)
        return cmd, out_file

    def get_seconds(self, time_str):
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)

    def parse_ffmpeg_output(self, line, total_duration):
        # Find time=00:00:00.00
        time_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", line)
        if time_match and total_duration > 0:
            current_time = self.get_seconds(time_match.group(1))
            progress = current_time / total_duration
            progress = min(max(progress, 0.0), 1.0)
            self.progress_bar.set(progress)
            self.prog_label.configure(text=f"Progress: {int(progress * 100)}%")

    def run_queue(self):
        self.is_converting = True
        self.convert_btn.configure(state="disabled", fg_color="gray", text="CONVERTING...")
        
        creationflags = 0x08000000 if os.name == 'nt' else 0

        for idx, infile in enumerate(self.queue):
            self.log(f"\n[{idx+1}/{len(self.queue)}] Processing: {os.path.basename(infile)}")
            cmd, outfile = self.build_command(infile)
            self.log("Command: " + " ".join(cmd))
            
            try:
                self.current_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    text=True, bufsize=1, universal_newlines=True, creationflags=creationflags
                )

                duration = 0.0
                
                if self.current_process.stdout:
                    for line in iter(self.current_process.stdout.readline, ""):
                        # Find duration: Duration: 00:00:10.00
                        dur_match = re.search(r"Duration:\s*(\d{2}:\d{2}:\d{2}\.\d{2})", line)
                        if dur_match:
                            duration = self.get_seconds(dur_match.group(1))
                            
                        self.after(0, self.parse_ffmpeg_output, line, duration)
                        
                    self.current_process.stdout.close()
                
                code = self.current_process.wait()
                if code == 0:
                    self.log(f"SUCCESS: {os.path.basename(outfile)}")
                else:
                    self.log(f"FAILED (Code {code}) on {os.path.basename(infile)}")
            except Exception as e:
                self.log(f"ERROR: {str(e)}")
                
        self.log("\nAll batch processing completed!")
        self.convert_btn.configure(state="normal", fg_color="#238636", text="START BATCH CONVERSION")
        self.is_converting = False
        self.progress_bar.set(0)
        self.prog_label.configure(text="Progress: 0%")

    def start_batch(self):
        if not self.queue:
            self.log("Queue is empty. Add files first.")
            return
        if self.is_converting:
            return
        threading.Thread(target=self.run_queue, daemon=True).start()

if __name__ == "__main__":
    ffmpeg_exec = os.path.join(get_resource_path("ffmpeg"), "bin", "ffmpeg.exe") if not getattr(sys, 'frozen', False) else get_resource_path("ffmpeg.exe")
    if not os.path.exists(ffmpeg_exec):
        print(f"Error: FFmpeg not found at {ffmpeg_exec}")
    app = FFmpegStudio()
    app.mainloop()
