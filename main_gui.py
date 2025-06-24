import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from tkinter import font as tkfont
import os
import json
from openrouter_client import OpenRouterClient
from generate_files import FileGenerator

class CodeGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Code Generator")
        self.root.geometry("900x700")
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure('TButton', padding=6, relief="flat", background="#ccc")
        self.style.configure('TLabel', padding=6)
        
        # Available models
        self.models = [
            "openai/gpt-4",
            "mistralai/mixtral-8x7b-instruct",
            "google/gemini-pro",
            "anthropic/claude-2"
        ]
        
        # Load settings
        self.settings_file = "settings.json"
        self.settings = self.load_settings()
        
        self.setup_ui()
    
    def load_settings(self):
        """Load application settings"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"api_key": "", "last_model": self.models[0], "output_dir": os.path.expanduser("~")}
    
    def save_settings(self):
        """Save application settings"""
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f)
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # API Key Frame
        api_frame = ttk.LabelFrame(main_frame, text="OpenRouter API Settings", padding="5")
        api_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(api_frame, text="API Key:").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar(value=self.settings.get("api_key", ""))
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=50, show="*")
        api_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Model Selection
        model_frame = ttk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=self.settings.get("last_model", self.models[0]))
        model_menu = ttk.OptionMenu(model_frame, self.model_var, self.model_var.get(), *self.models)
        model_menu.pack(side=tk.LEFT, padx=5)
        
        # Output Directory
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(output_frame, text="Output Directory:").pack(side=tk.LEFT)
        self.output_dir_var = tk.StringVar(value=self.settings.get("output_dir", os.path.expanduser("~")))
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var, width=50)
        output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        browse_btn = ttk.Button(output_frame, text="Browse...", command=self.browse_output_dir)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Prompt Frame
        prompt_frame = ttk.LabelFrame(main_frame, text="Enter Your Prompt", padding="5")
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, height=8, font=('Segoe UI', 10))
        self.prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons Frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.generate_btn = ttk.Button(btn_frame, text="Generate Code", command=self.generate_code)
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.download_btn = ttk.Button(btn_frame, text="Download Project", command=self.download_project, state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        # Preview Frame
        preview_frame = ttk.LabelFrame(main_frame, text="Code Preview", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame, 
            wrap=tk.NONE, 
            font=('Consolas', 10),
            bg='#f5f5f5',
            insertbackground='black',
            selectbackground='#6fa8dc',
            inactiveselectbackground='#6fa8dc',
            padx=10,
            pady=10
        )
        
        # Add line numbers
        self.line_numbers = tk.Text(preview_frame, width=4, padx=3, takefocus=0, border=0,
                                   background='#e0e0e0', state='disabled', wrap='none')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Add scrollbars
        y_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        x_scroll = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.preview_text.xview)
        self.preview_text.configure(yscrollcommand=self.update_scrollbars, xscrollcommand=x_scroll.set)
        
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.preview_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Bind events
        self.preview_text.bind('<KeyRelease>', self.on_text_change)
        self.preview_text.bind('<MouseWheel>', self.on_mousewheel)
        self.preview_text.bind('<Button-4>', self.on_mousewheel)
        self.preview_text.bind('<Button-5>', self.on_mousewheel)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize
        self.update_status("Ready")
        self.update_line_numbers()
    
    def browse_output_dir(self):
        """Open a directory selection dialog"""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
    
    def update_status(self, message):
        """Update status bar"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def update_scrollbars(self, *args):
        """Update scrollbars and line numbers"""
        self.preview_text.yview_moveto(args[0])
        self.update_line_numbers()
    
    def on_text_change(self, event=None):
        """Handle text changes in the preview"""
        self.update_line_numbers()
    
    def on_mousewheel(self, event):
        """Handle mousewheel events for scrolling"""
        if event.num == 4 or event.delta > 0:
            self.preview_text.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.preview_text.yview_scroll(1, "units")
        self.update_line_numbers()
        return "break"
    
    def update_line_numbers(self, event=None):
        """Update line numbers in the preview"""
        # Get current scroll position
        first_visible_line = int(self.preview_text.index("@0,0").split('.')[0])
        last_visible_line = int(self.preview_text.index(f"@0,{self.preview_text.winfo_height()}").split('.')[0])
        
        # Get total lines
        line_count = int(self.preview_text.index('end-1c').split('.')[0]) if self.preview_text.get('1.0', 'end-1c') else 0
        
        # Update line numbers
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete(1.0, tk.END)
        
        for i in range(first_visible_line, min(last_visible_line + 2, line_count + 1)):
            self.line_numbers.insert(tk.END, f"{i}\n")
        
        self.line_numbers.config(state=tk.DISABLED)
    
    def generate_code(self):
        """Generate code based on the prompt"""
        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showerror("Error", "Please enter a prompt")
            return
        
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter your OpenRouter API key")
            return
        
        # Update settings
        self.settings["api_key"] = api_key
        self.settings["last_model"] = self.model_var.get()
        self.settings["output_dir"] = self.output_dir_var.get()
        self.save_settings()
        
        # Set up client
        try:
            client = OpenRouterClient(api_key)
            self.update_status("Generating code...")
            self.generate_btn.config(state=tk.DISABLED)
            self.root.update()
            
            # Generate code
            self.generated_files = FileGenerator.generate_from_prompt(
                prompt=prompt,
                output_dir=self.settings["output_dir"],
                client=client
            )
            
            # Display first file in preview
            if self.generated_files:
                with open(self.generated_files[0], 'r', encoding='utf-8') as f:
                    self.preview_text.delete(1.0, tk.END)
                    self.preview_text.insert(tk.END, f.read())
                
                self.download_btn.config(state=tk.NORMAL)
                self.update_status(f"Generated {len(self.generated_files)} files. First file: {os.path.basename(self.generated_files[0])}")
            else:
                self.update_status("No files were generated")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate code: {str(e)}")
            self.update_status("Error generating code")
        finally:
            self.generate_btn.config(state=tk.NORMAL)
    
    def download_project(self):
        """Create a zip file of the generated project"""
        if not hasattr(self, 'generated_files') or not self.generated_files:
            messagebox.showerror("Error", "No files to download")
            return
        
        try:
            import zipfile
            from datetime import datetime
            
            # Create zip filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = os.path.join(os.path.dirname(self.generated_files[0]), f"generated_project_{timestamp}.zip")
            
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in self.generated_files:
                    # Calculate the relative path for the zip file
                    rel_path = os.path.relpath(file, os.path.dirname(self.generated_files[0]))
                    zipf.write(file, rel_path)
            
            messagebox.showinfo("Success", f"Project saved as {zip_filename}")
            self.update_status(f"Project saved as {os.path.basename(zip_filename)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create zip file: {str(e)}")
            self.update_status("Error creating zip file")

def main():
    root = tk.Tk()
    app = CodeGeneratorApp(root)
    
    # Set application icon if available
    try:
        root.iconbitmap("icon.ico")  # You can add an icon file to the same directory
    except:
        pass
    
    # Set minimum window size
    root.minsize(800, 600)
    
    # Center the window
    window_width = 900
    window_height = 700
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Set application style
    root.tk_setPalette(background='#ffffff')
    
    # Run the application
    root.mainloop()

if __name__ == "__main__":
    main()
