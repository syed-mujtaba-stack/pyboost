import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Dict, Any
import re

class EnhancedTextEditor(scrolledtext.ScrolledText):
    """Enhanced text editor with line numbers and syntax highlighting"""
    
    def __init__(self, master=None, **kwargs):
        # Configure default options
        kwargs.setdefault('wrap', 'none')
        kwargs.setdefault('font', ('Consolas', 12))
        kwargs.setdefault('undo', True)
        kwargs.setdefault('autoseparators', True)
        kwargs.setdefault('maxundo', -1)
        
        # Create main frame
        self.frame = ttk.Frame(master)
        
        # Create line numbers widget
        self.line_numbers = tk.Text(
            self.frame,
            width=4,
            padx=3,
            takefocus=0,
            border=0,
            background='#f0f0f0',
            foreground='#666666',
            state='disabled',
            wrap='none'
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Initialize the scrolled text widget
        super().__init__(self.frame, **{k: v for k, v in kwargs.items() if k != 'master'})
        self.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure tags for syntax highlighting
        self.tag_configure("keyword", foreground="#569cd6")
        self.tag_configure("string", foreground="#ce9178")
        self.tag_configure("number", foreground="#b5cea8")
        self.tag_configure("comment", foreground="#6a9955")
        self.tag_configure("function", foreground="#dcdcaa")
        self.tag_configure("class", foreground="#4ec9b0")
        self.tag_configure("operator", foreground="#d4d4d4")
        self.tag_configure("current_line", background="#f5f5f5")
        
        # Bind events
        self.bind('<KeyRelease>', self.on_key_release)
        self.bind('<Button-1>', self.on_click)
        self.bind('<MouseWheel>', self.on_mousewheel)
        self.bind('<Configure>', self.on_configure)
        
        # Initialize line numbers
        self.update_line_numbers()
    
    def pack(self, **kwargs):
        """Pack the frame instead of the text widget"""
        return self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Grid the frame instead of the text widget"""
        return self.frame.grid(**kwargs)
    
    def place(self, **kwargs):
        """Place the frame instead of the text widget"""
        return self.frame.place(**kwargs)
    
    def pack_forget(self):
        """Forget the frame"""
        return self.frame.pack_forget()
    
    def grid_forget(self):
        """Forget the frame"""
        return self.frame.grid_forget()
    
    def place_forget(self):
        """Forget the frame"""
        return self.frame.place_forget()
    
    def on_key_release(self, event=None):
        """Handle key release events"""
        self.update_line_numbers()
        self.highlight_syntax()
        self.highlight_current_line()
        
        # Auto-indent on newline
        if event and event.keysym == "Return":
            self.auto_indent()
    
    def on_click(self, event=None):
        """Handle mouse click events"""
        self.update_line_numbers()
        self.highlight_current_line()
    
    def on_mousewheel(self, event):
        """Handle mouse wheel events"""
        if event.num == 5 or event.delta < 0:
            self.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.yview_scroll(-1, "units")
        self.update_line_numbers()
        return "break"
    
    def on_configure(self, event=None):
        """Handle window configuration changes"""
        self.update_line_numbers()
    
    def update_line_numbers(self):
        """Update the line numbers in the sidebar"""
        # Get current view
        first_visible = self.yview()[0]
        last_visible = self.yview()[1]
        
        # Get total number of lines
        total_lines = int(self.index(tk.END).split('.')[0])
        
        # Calculate visible lines
        first_line = int(first_visible * total_lines) + 1
        last_line = int(last_visible * total_lines) + 1
        
        # Generate line numbers
        line_numbers = '\n'.join(str(i) for i in range(first_line, last_line + 1))
        
        # Update line numbers widget
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete(1.0, tk.END)
        self.line_numbers.insert(1.0, line_numbers)
        self.line_numbers.config(state=tk.DISABLED)
        
        # Update scroll region
        self.line_numbers.yview_moveto(first_visible)
    
    def highlight_current_line(self, event=None):
        """Highlight the current line"""
        self.tag_remove("current_line", "1.0", tk.END)
        
        # Get current line
        current_line = self.index(tk.INSERT).split('.')[0]
        
        # Add highlight to current line
        self.tag_add("current_line", f"{current_line}.0", f"{current_line}.0 lineend")
    
    def auto_indent(self, event=None):
        """Auto-indent the current line"""
        # Get current line and previous line
        current_line = self.index(tk.INSERT).split('.')[0]
        prev_line = str(int(current_line) - 1)
        
        # Get indentation of previous line
        prev_text = self.get(f"{prev_line}.0", f"{prev_line}.end")
        indent = len(prev_text) - len(prev_text.lstrip())
        
        # Apply indentation to current line
        self.insert(tk.INSERT, ' ' * indent)
        
        # If previous line ends with ':', add an extra level of indentation
        if prev_text.rstrip().endswith(':'):
            self.insert(tk.INSERT, '    ')  # 4 spaces for Python
        
        return "break"
    
    def highlight_syntax(self, event=None):
        """Apply syntax highlighting to the text"""
        # Clear existing tags
        for tag in ["keyword", "string", "number", "comment", "function", "class", "operator"]:
            self.tag_remove(tag, "1.0", tk.END)
        
        # Get the text
        text = self.get("1.0", tk.END)
        
        # Simple syntax highlighting (can be enhanced with a proper lexer)
        self.highlight_pattern(r"\b(and|as|assert|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield|True|False|None)\b", "keyword")
        self.highlight_pattern(r'"[^"]*"|\'[^\']*\'', "string")
        self.highlight_pattern(r'\b\d+\b', "number")
        self.highlight_pattern(r'#[^\n]*', "comment")
        self.highlight_pattern(r'\b(def|class)\s+(\w+)', "function", group=2)
        self.highlight_pattern(r'(\+|\-|\*|/|//|%|\*\*|==|!=|<=|>=|<|>|=|\+=|\-=|\*=|/=|//=|%=|\*\*=|&=|\|=|\^=|>>=|<<=)', "operator")
    
    def highlight_pattern(self, pattern, tag, group=0):
        """Highlight a regex pattern in the text"""
        text = self.get("1.0", tk.END)
        
        # Find all matches
        import re
        matches = [(m.start(group), m.end(group)) for m in re.finditer(pattern, text, re.MULTILINE)]
        
        # Apply tags to matches
        for start, end in matches:
            self.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
