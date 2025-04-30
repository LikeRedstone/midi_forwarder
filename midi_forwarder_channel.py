import mido
import tkinter as tk
from tkinter import ttk
from threading import Thread
from queue import Queue

class MidiForwarderOctaveShift:
    def __init__(self, root):
        self.root = root
        self.root.title("MidiUnion")
        self.root.geometry("841x655")
        
        # Configuration
        self.input_port = None
        self.output_port = None
        self.running = False
        self.channel = None
        self.message_queue = Queue()
        self.octave_offset = 4  # Default octave shift (shows octaves 4-5)
        self.keys = []
        
        # Create frames
        control_frame = ttk.Frame(root, padding=10)
        control_frame.pack(fill='x')
        
        piano_frame = ttk.Frame(root)
        piano_frame.pack(fill='both', expand=True, pady=10)
        
        # Setup controls
        self.setup_controls(control_frame)
        
        # Setup piano (fixed 2 octaves)
        self.setup_piano(piano_frame)
        
        # Initialize
        self.refresh_devices()
        self.update_message_display()
        
    def setup_controls(self, parent):
        """Setup control panel with device selection and options"""
        # Device selection
        ttk.Label(parent, text="Input Device:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.input_var = tk.StringVar()
        self.input_dropdown = ttk.Combobox(parent, textvariable=self.input_var, width=30)
        self.input_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        ttk.Label(parent, text="Output Device:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.output_var = tk.StringVar()
        self.output_dropdown = ttk.Combobox(parent, textvariable=self.output_var, width=30)
        self.output_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        
        # Channel selection
        # Remove per-octave channel selectors and replace with cutoff octave and two channel selectors
        ttk.Label(parent, text="Cutoff Octave:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.cutoff_octave_var = tk.IntVar(value=self.octave_offset + 4)
        self.cutoff_spinbox = ttk.Spinbox(parent, from_=-1, to=9, textvariable=self.cutoff_octave_var, width=5)
        self.cutoff_spinbox.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(parent, text="Channel for Octaves Below Cutoff:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.channel_below_var = tk.StringVar(value="Omni (0)")
        self.channel_below_cb = ttk.Combobox(parent, textvariable=self.channel_below_var, values=["Omni (0)"] + [str(i) for i in range(1,17)], width=10)
        self.channel_below_cb.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(parent, text="Octave shift for Channel Below Cutoff:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        self.octave_below_var = tk.IntVar(value=0)
        self.octave_below_spinbox = ttk.Spinbox(parent, from_=-4, to=6, textvariable=self.octave_below_var, width=5)
        self.octave_below_spinbox.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(parent, text="Channel for Octaves At or Above Cutoff:").grid(row=5, column=0, padx=5, pady=5, sticky='w')
        self.channel_above_var = tk.StringVar(value="Omni (0)")
        self.channel_above_cb = ttk.Combobox(parent, textvariable=self.channel_above_var, values=["Omni (0)"] + [str(i) for i in range(1,17)], width=10)
        self.channel_above_cb.grid(row=5, column=1, padx=5, pady=5, sticky='w')
        
        ttk.Label(parent, text="Octave shift for Channel At or Above Cutoff:").grid(row=6, column=0, padx=5, pady=5, sticky='w')
        self.octave_above_var = tk.IntVar(value=0)
        self.octave_above_spinbox = ttk.Spinbox(parent, from_=-4, to=6, textvariable=self.octave_above_var, width=5)
        self.octave_above_spinbox.grid(row=6, column=1, padx=5, pady=5, sticky='w')
        
        # Octave shift slider
        ttk.Label(parent, text="Octave Shift:").grid(row=7, column=0, padx=5, pady=5, sticky='w')
        self.octave_slider = ttk.Scale(parent, from_=-4, to=6, orient='horizontal', 
                                     command=lambda v: self.set_octave_offset(int(float(v))))
        self.octave_slider.set(0)  # Default to octave 4
        self.octave_slider.grid(row=7, column=1, padx=5, pady=5, sticky='ew')
        ttk.Label(parent, text="(Shifts displayed octave range)").grid(row=8, column=1, sticky='w')
        
        # Control buttons frame
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=10, column=0, columnspan=2, pady=5, sticky='w')
        
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_forwarding)
        self.start_btn.pack(side='left', padx=1)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_forwarding, state='disabled')
        self.stop_btn.pack(side='left', padx=15)
        
        # Message log frame
        msg_frame = ttk.Frame(parent)
        msg_frame.grid(row=11, column=0, columnspan=2, sticky='ew')
        ttk.Label(msg_frame, text="MIDI Messages:").pack(anchor='w')
        import tkinter.font as tkfont
        monospace_font = tkfont.Font(family="Courier", size=10)
        self.message_log = tk.Text(msg_frame, height=4, width=60, state='disabled', bg='white', relief='sunken', font=monospace_font)
        self.message_log.pack(fill='x')
        
        # Status frame
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=12, column=0, columnspan=2, sticky='ew')
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor='w', padx=5)
    
    def setup_piano(self, parent):
        """Setup piano keyboard visualization (fixed 3 octaves)"""
        self.piano_canvas = tk.Canvas(parent, bg='#f0f0f0', highlightthickness=0)
        self.piano_canvas.pack(fill='both', expand=True)
        self.draw_piano()
    
    def draw_piano(self):
        """Draw piano keys (always 3 octaves) with current octave offset"""
        self.piano_canvas.delete("all")
        self.keys = []
        
        key_width = 40
        key_height = 200
        black_width = key_width * 0.6
        black_height = key_height * 0.6
        
        # Draw white keys (3 octaves)
        for octave in range(3):
            base_octave = self.octave_offset + octave
            for i in range(7):
                x = (octave * 7 + i) * key_width
                key_id = self.piano_canvas.create_rectangle(
                    x, 0, x + key_width, key_height,
                    fill='white', outline='black', width=1, tags=('key', 'white')
                )
                note = ['C', 'D', 'E', 'F', 'G', 'A', 'B'][i] + str(base_octave + 4)
                self.keys.append((note, key_id, 'white'))
                
                # Add note label
                self.piano_canvas.create_text(
                    x + key_width/2, key_height - 20,
                    text=note, font=('Arial', 10), tags=('label', 'white_label')
                )
        
        # Draw black keys (3 octaves)
        for octave in range(3):
            base_octave = self.octave_offset + octave
            for i, offset in enumerate([0, 1, 0, 1, 1, 0, 1]):
                if i in [2, 6]: continue  # Skip E and B
                x = (octave * 7 + i) * key_width + key_width - black_width/2
                key_id = self.piano_canvas.create_rectangle(
                    x, 0, x + black_width, black_height,
                    fill='black', outline='black', width=1, tags=('key', 'black')
                )
                note = ['C#', 'D#', '', 'F#', 'G#', 'A#', ''][i] + str(base_octave + 4)
                self.keys.append((note, key_id, 'black'))
    
    def set_octave_offset(self, offset):
        """Update octave shift and redraw piano"""
        self.octave_offset = offset
        self.draw_piano()
        self.status_var.set(f"Showing octaves {self.octave_offset+4}-{self.octave_offset+6}")
    
    def refresh_devices(self):
        """Refresh available MIDI devices"""
        inputs = mido.get_input_names()
        outputs = mido.get_output_names()
        
        self.input_dropdown['values'] = inputs
        self.output_dropdown['values'] = outputs
        
        if inputs: self.input_var.set(inputs[0])
        if outputs: self.output_var.set(outputs[0])
    
    def start_forwarding(self):
        """Start MIDI forwarding"""
        input_name = self.input_var.get()
        output_name = self.output_var.get()
        
        if not input_name or not output_name:
            self.status_var.set("Select input and output devices")
            return
            
        try:
            # Set cutoff octave and channels
            self.cutoff_octave = self.cutoff_octave_var.get()
            
            channel_below_str = self.channel_below_var.get()
            if channel_below_str == "Omni (0)":
                self.channel_below = None
            else:
                self.channel_below = int(channel_below_str) - 1
            
            channel_above_str = self.channel_above_var.get()
            if channel_above_str == "Omni (0)":
                self.channel_above = None
            else:
                self.channel_above = int(channel_above_str) - 1
            
            # Set octave offsets for channels
            self.octave_below_offset = self.octave_below_var.get()
            self.octave_above_offset = self.octave_above_var.get()
            
            # Open ports
            self.input_port = mido.open_input(input_name)
            self.output_port = mido.open_output(output_name)
            self.running = True
            
            # Update UI
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.status_var.set(f"Forwarding from {input_name} to channel {channel_below_str} and {channel_above_str}")
            
            # Start forwarding thread
            Thread(target=self.forward_messages, daemon=True).start()
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
    
    def stop_forwarding(self):
        """Stop MIDI forwarding"""
        self.running = False
        if self.input_port: self.input_port.close()
        if self.output_port: self.output_port.close()
        
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_var.set("Stopped")
    
    def forward_messages(self):
        """Forward MIDI messages in background"""
        while self.running:
            try:
                for msg in self.input_port.iter_pending():
                    # Determine octave of note and set channel based on cutoff
                    if hasattr(msg, 'note') and hasattr(msg, 'channel'):
                        note_octave = (msg.note // 12) - 1  # MIDI octave number
                        if note_octave < self.cutoff_octave:
                            if self.channel_below is not None:
                                msg.channel = self.channel_below
                                # Apply octave offset for below cutoff channel
                                new_note = msg.note + (self.octave_below_offset * 12)
                                if 0 <= new_note <= 127:
                                    msg.note = new_note
                        else:
                            if self.channel_above is not None:
                                msg.channel = self.channel_above
                                # Apply octave offset for above cutoff channel
                                new_note = msg.note + (self.octave_above_offset * 12)
                                if 0 <= new_note <= 127:
                                    msg.note = new_note
                    
                    # Forward message
                    self.output_port.send(msg)
                    
                    # Log message
                    self.message_queue.put(str(msg))
                    
                    # Highlight keys
                    if msg.type == 'note_on' and msg.velocity > 0:
                        self.highlight_key(msg.note)
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        self.unhighlight_key(msg.note)
                        
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                self.stop_forwarding()
    
    def highlight_key(self, note_num):
        """Highlight piano key for note"""
        note_name = self.midi_to_note(note_num)
        for note, key_id, key_type in self.keys:
            if note == note_name:
                color = '#ff6666' if key_type == 'black' else '#6699ff'
                self.piano_canvas.itemconfig(key_id, fill=color)
                break
    
    def unhighlight_key(self, note_num):
        """Unhighlight piano key for note"""
        note_name = self.midi_to_note(note_num)
        for note, key_id, key_type in self.keys:
            if note == note_name:
                color = 'black' if key_type == 'black' else 'white'
                self.piano_canvas.itemconfig(key_id, fill=color)
                break
    
    def midi_to_note(self, note_num):
        """Convert MIDI note number to note name with current octave offset"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note_num // 12) - 1
        note = notes[note_num % 12]
        return f"{note}{octave}"
    
    def update_message_display(self):
        """Update message log display"""
        while not self.message_queue.empty():
            msg = self.message_queue.get()
            # Truncate message to 60 characters to prevent expansion
            truncated_msg = msg[:60]
            self.message_log.config(state='normal')
            self.message_log.insert('end', truncated_msg + '\n')
            
            # Keep last 3 messages
            lines = self.message_log.get('1.0', 'end-1c').split('\n')
            if len(lines) > 3:
                self.message_log.delete('1.0', f"{len(lines)-3}.0")
            
            self.message_log.config(state='disabled')
            self.message_log.see('end')
        
        self.root.after(100, self.update_message_display)

if __name__ == "__main__":
    root = tk.Tk()
    app = MidiForwarderOctaveShift(root)
    root.mainloop()
