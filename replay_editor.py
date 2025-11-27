"""
Interactive Replay Editor GUI

Provides a tkinter-based interface for inspecting and modifying
replay events during playback.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from pathlib import Path
from typing import Optional, List
from replay_index import ReplayIndex, ActionEvent


class ReplayEditor:
    """
    Interactive GUI editor for replay modification.
    
    Features:
    - View filtered list of significant events (clicks, keys, scrolls)
    - Edit event properties (coordinates, keys, timing)
    - Insert new events before/after existing ones
    - Delete events
    - Save changes atomically
    """
    
    def __init__(self, macro, current_event_idx: int):
        """
        Initialize editor.
        
        Args:
            macro: Macro instance with events
            current_event_idx: Current position in replay
        """
        self.macro = macro
        self.current_idx = current_event_idx
        self.index = ReplayIndex(macro.events)
        self.modified = False
        self.window = None
        self.selected_action_idx = None
        self.play_from_idx = None  # Index to play from (if user clicks "Play from here")
        
        # UI elements
        self.event_listbox = None
        self.detail_frame = None
        self.stats_label = None
        
        # Filter settings (will be initialized after window creation)
        self.show_clicks = None
        self.show_keys = None
        self.show_scrolls = None
        self.show_moves = None
    
    def show(self):
        """Display editor window (blocks until closed)"""
        self.window = tk.Tk()
        self.window.title("Replay Editor - Paused")
        self.window.geometry("900x700")
        
        # Initialize BooleanVars after window creation
        self.show_clicks = tk.BooleanVar(value=True)
        self.show_keys = tk.BooleanVar(value=True)
        self.show_scrolls = tk.BooleanVar(value=True)
        self.show_moves = tk.BooleanVar(value=False)
        
        # Make window stay on top
        self.window.attributes('-topmost', True)
        
        self._build_ui()
        self._populate_event_list()
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
        
        # Run event loop
        self.window.mainloop()
    
    def _build_ui(self):
        """Build the user interface"""
        # Top: Statistics and current position
        top_frame = ttk.Frame(self.window, padding="10")
        top_frame.pack(fill=tk.X)
        
        stats = self.index.get_statistics()
        current_time = self.macro.events[self.current_idx].t if self.current_idx < len(self.macro.events) else 0
        
        self.stats_label = ttk.Label(
            top_frame,
            text=f"📊 Total: {stats['total_events']} events | "
                 f"Actions: {stats['action_events']} | "
                 f"Moves: {stats['total_moves']} | "
                 f"⏱️ Current: {current_time:.2f}s (Event #{self.current_idx})",
            font=('Arial', 10, 'bold')
        )
        self.stats_label.pack()
        
        # Filter controls
        filter_frame = ttk.LabelFrame(self.window, text="Filters", padding="10")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(filter_frame, text="Clicks", variable=self.show_clicks, 
                       command=self._populate_event_list).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(filter_frame, text="Keys", variable=self.show_keys,
                       command=self._populate_event_list).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(filter_frame, text="Scrolls", variable=self.show_scrolls,
                       command=self._populate_event_list).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(filter_frame, text="Mouse Moves", variable=self.show_moves,
                       command=self._populate_event_list).pack(side=tk.LEFT, padx=5)
        
        # Event list
        list_frame = ttk.LabelFrame(self.window, text="Events", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview with columns
        columns = ('time', 'type', 'data')
        self.event_listbox = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=15)
        
        self.event_listbox.heading('#0', text='#')
        self.event_listbox.heading('time', text='Time')
        self.event_listbox.heading('type', text='Type')
        self.event_listbox.heading('data', text='Data')
        
        self.event_listbox.column('#0', width=60)
        self.event_listbox.column('time', width=80)
        self.event_listbox.column('type', width=100)
        self.event_listbox.column('data', width=500)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.event_listbox.yview)
        self.event_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.event_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection
        self.event_listbox.bind('<<TreeviewSelect>>', self._on_event_select)
        
        # Detail editor
        detail_frame = ttk.LabelFrame(self.window, text="Event Details", padding="10")
        detail_frame.pack(fill=tk.BOTH, padx=10, pady=5)
        
        self.detail_text = scrolledtext.ScrolledText(detail_frame, height=8, wrap=tk.WORD)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # Action buttons
        action_frame = ttk.Frame(self.window, padding="10")
        action_frame.pack(fill=tk.X)
        
        ttk.Button(action_frame, text="👁️ Preview Position", 
                  command=self._preview_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="▶️ Play from here", 
                  command=self._play_from_here).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Insert Before", 
                  command=self._insert_before).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Insert After", 
                  command=self._insert_after).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Modify", 
                  command=self._modify_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Delete", 
                  command=self._delete_event).pack(side=tk.LEFT, padx=5)
        
        # Bottom: Control buttons
        control_frame = ttk.Frame(self.window, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Button(control_frame, text="💾 Save & Resume (F7)", 
                  command=self._save_and_resume, 
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="❌ Discard Changes", 
                  command=self._discard).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="⏹️ Stop Replay (F5)", 
                  command=self._stop_replay).pack(side=tk.LEFT, padx=5)
        
        # Keyboard shortcuts
        self.window.bind('<F7>', lambda e: self._save_and_resume())
        self.window.bind('<F5>', lambda e: self._stop_replay())
        self.window.bind('<Escape>', lambda e: self._discard())
    
    def _populate_event_list(self):
        """Populate event list based on filters"""
        # Clear existing
        for item in self.event_listbox.get_children():
            self.event_listbox.delete(item)
        
        # Build filter list
        event_types = []
        if self.show_clicks.get():
            event_types.extend(['m_down', 'm_up'])
        if self.show_keys.get():
            event_types.extend(['k_down', 'k_up'])
        if self.show_scrolls.get():
            event_types.append('m_scroll')
        if self.show_moves.get():
            event_types.append('m_move')
        
        # Get filtered events
        if self.show_moves.get():
            # Show all events
            filtered = [ActionEvent(i, e.t, e.type, e.data) 
                       for i, e in enumerate(self.macro.events) 
                       if e.type in event_types]
        else:
            # Use index for efficiency
            filtered = self.index.filter_by_type(event_types)
        
        # Populate list
        for action in filtered:
            # Format data for display
            data_str = self._format_event_data(action.type, action.data)
            
            # Highlight current event
            tags = ()
            if action.index == self.current_idx:
                tags = ('current',)
            
            self.event_listbox.insert('', tk.END, 
                                     text=f"{action.index}",
                                     values=(f"{action.t:.2f}s", action.type, data_str),
                                     tags=tags)
        
        # Configure tag colors
        self.event_listbox.tag_configure('current', background='lightblue', font=('Arial', 9, 'bold'))
    
    def _format_event_data(self, event_type: str, data: dict) -> str:
        """Format event data for display"""
        if event_type in ['m_move', 'm_down', 'm_up']:
            x, y = data.get('x', 0), data.get('y', 0)
            button = data.get('button', '')
            if button:
                return f"x:{x}, y:{y}, {button.split('.')[-1]}"
            return f"x:{x}, y:{y}"
        elif event_type in ['k_down', 'k_up']:
            return f"key: {data.get('key', '')}"
        elif event_type == 'm_scroll':
            return f"x:{data.get('x', 0)}, y:{data.get('y', 0)}, dx:{data.get('dx', 0)}, dy:{data.get('dy', 0)}"
        else:
            return str(data)
    
    def _on_event_select(self, event):
        """Handle event selection"""
        selection = self.event_listbox.selection()
        if not selection:
            return
        
        item = self.event_listbox.item(selection[0])
        self.selected_action_idx = int(item['text'])
        
        # Show details
        event_obj = self.macro.events[self.selected_action_idx]
        details = {
            'index': self.selected_action_idx,
            'time': event_obj.t,
            'type': event_obj.type,
            'data': event_obj.data
        }
        
        self.detail_text.delete('1.0', tk.END)
        self.detail_text.insert('1.0', json.dumps(details, indent=2))
    
    def _preview_position(self):
        """Move mouse to the selected action's position without executing replay"""
        if self.selected_action_idx is None:
            messagebox.showwarning("No Selection", "Please select an event first")
            return
        
        event = self.macro.events[self.selected_action_idx]
        
        # Only preview events with coordinates
        if event.type not in ['m_move', 'm_down', 'm_up', 'm_scroll']:
            messagebox.showinfo("Preview", 
                              f"Event type '{event.type}' has no position to preview.\n"
                              f"This feature works with mouse events only.")
            return
        
        try:
            from pynput import mouse
            
            # Get coordinates
            x = event.data.get('x', 0)
            y = event.data.get('y', 0)
            
            # Apply coordinate transformation if available
            if self.macro.resolution_transform:
                x_ratio, y_ratio = self.macro.resolution_transform
                x_new = round(x * x_ratio)
                y_new = round(y * y_ratio)
                
                # Clamp to screen bounds
                if self.macro.cached_resolution:
                    max_x, max_y = self.macro.cached_resolution
                    x_new = max(0, min(x_new, max_x - 1))
                    y_new = max(0, min(y_new, max_y - 1))
                
                x, y = x_new, y_new
            
            # Move mouse to position
            ms = mouse.Controller()
            ms.position = (x, y)
            
            # Show confirmation
            event_type_name = {
                'm_move': 'Mouse Move',
                'm_down': 'Mouse Down',
                'm_up': 'Mouse Up',
                'm_scroll': 'Mouse Scroll'
            }.get(event.type, event.type)
            
            print(f"👁️ Preview: Moved mouse to ({x}, {y}) for {event_type_name} at {event.t:.2f}s")
            
            # Update status in window title temporarily
            original_title = self.window.title()
            self.window.title(f"✓ Previewed position ({x}, {y})")
            self.window.after(2000, lambda: self.window.title(original_title))
            
        except Exception as e:
            messagebox.showerror("Preview Error", f"Failed to preview position: {e}")
    
    def _play_from_here(self):
        """Jump to selected event and resume replay from there"""
        if self.selected_action_idx is None:
            messagebox.showwarning("No Selection", "Please select an event first")
            return
        
        # Set the play_from_idx to tell the replay loop where to jump
        self.play_from_idx = self.selected_action_idx
        
        # Update current_idx in macro so replay continues from here
        self.macro.current_replay_idx = self.selected_action_idx
        
        # Resume replay
        self.macro.paused = False
        self.window.destroy()
        
        print(f"▶️ Jumping to event #{self.selected_action_idx} and resuming...")
    
    def _insert_before(self):
        """Insert new event before selected"""
        if self.selected_action_idx is None:
            messagebox.showwarning("No Selection", "Please select an event first")
            return
        
        self._show_insert_dialog('before')
    
    def _insert_after(self):
        """Insert new event after selected"""
        if self.selected_action_idx is None:
            messagebox.showwarning("No Selection", "Please select an event first")
            return
        
        self._show_insert_dialog('after')
    
    def _show_insert_dialog(self, position: str):
        """Show dialog for inserting new event"""
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Insert Event {position.title()}")
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text="Event Type:").pack(pady=5)
        event_type = ttk.Combobox(dialog, values=['m_down', 'm_up', 'k_down', 'k_up', 'm_scroll'])
        event_type.pack(pady=5)
        event_type.set('m_down')
        
        ttk.Label(dialog, text="Event Data (JSON):").pack(pady=5)
        data_text = scrolledtext.ScrolledText(dialog, height=10)
        data_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        data_text.insert('1.0', '{"x": 0, "y": 0, "button": "Button.left"}')
        
        def insert():
            try:
                from dataclasses import dataclass
                # Parse data
                data = json.loads(data_text.get('1.0', tk.END))
                
                # Get timing
                ref_event = self.macro.events[self.selected_action_idx]
                new_time = ref_event.t + (0.1 if position == 'after' else -0.1)
                
                # Create new event
                @dataclass
                class Event:
                    t: float
                    type: str
                    data: dict
                
                new_event = Event(new_time, event_type.get(), data)
                
                # Insert
                insert_idx = self.selected_action_idx + (1 if position == 'after' else 0)
                self.macro.events.insert(insert_idx, new_event)
                
                self.modified = True
                self.index = ReplayIndex(self.macro.events)  # Rebuild index
                self._populate_event_list()
                
                dialog.destroy()
                messagebox.showinfo("Success", f"Event inserted {position}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to insert event: {e}")
        
        ttk.Button(dialog, text="Insert", command=insert).pack(pady=10)
    
    def _modify_event(self):
        """Modify selected event"""
        if self.selected_action_idx is None:
            messagebox.showwarning("No Selection", "Please select an event first")
            return
        
        try:
            # Parse modified data from detail text
            details = json.loads(self.detail_text.get('1.0', tk.END))
            
            # Update event
            event = self.macro.events[self.selected_action_idx]
            event.t = details['time']
            event.type = details['type']
            event.data = details['data']
            
            self.modified = True
            self.index = ReplayIndex(self.macro.events)  # Rebuild index
            self._populate_event_list()
            
            messagebox.showinfo("Success", "Event modified")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to modify event: {e}")
    
    def _delete_event(self):
        """Delete selected event"""
        if self.selected_action_idx is None:
            messagebox.showwarning("No Selection", "Please select an event first")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this event?"):
            del self.macro.events[self.selected_action_idx]
            self.modified = True
            self.selected_action_idx = None
            self.index = ReplayIndex(self.macro.events)  # Rebuild index
            self._populate_event_list()
            self.detail_text.delete('1.0', tk.END)
    
    def _save_and_resume(self):
        """Save changes and resume replay"""
        if self.modified:
            if self._save_changes():
                self.macro.paused = False
                self.window.destroy()
        else:
            self.macro.paused = False
            self.window.destroy()
    
    def _discard(self):
        """Discard changes and resume"""
        if self.modified:
            if messagebox.askyesno("Discard Changes", "Discard all changes?"):
                self.macro.paused = False
                self.window.destroy()
        else:
            self.macro.paused = False
            self.window.destroy()
    
    def _stop_replay(self):
        """Stop replay completely"""
        self.macro.should_stop = True
        self.window.destroy()
    
    def _save_changes(self) -> bool:
        """
        Save modified events back to JSON file atomically.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for saving
            if self.macro.recording_metadata:
                # New format with metadata
                from dataclasses import asdict
                payload = {
                    'metadata': asdict(self.macro.recording_metadata),
                    'events': [asdict(e) for e in self.macro.events]
                }
            else:
                # Old format
                from dataclasses import asdict
                payload = [asdict(e) for e in self.macro.events]
            
            # Atomic write: write to temp file, then rename
            temp_file = self.macro.file.with_suffix('.json.tmp')
            backup_file = self.macro.file.with_suffix('.json.backup')
            
            # Write to temp
            temp_file.write_text(json.dumps(payload, indent=2))
            
            # Backup original
            if self.macro.file.exists():
                import shutil
                shutil.copy2(self.macro.file, backup_file)
            
            # Replace original
            temp_file.replace(self.macro.file)
            
            print(f"✅ Saved {len(self.macro.events)} events to {self.macro.file}")
            messagebox.showinfo("Success", "Changes saved successfully!")
            return True
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save changes: {e}")
            return False


if __name__ == "__main__":
    # Test the editor
    print("ReplayEditor module loaded successfully")
