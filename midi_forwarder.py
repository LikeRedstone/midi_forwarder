import mido
import tkinter as tk
from tkinter import ttk
from threading import Thread
from queue import Queue

class MidiForwarderOctaveShift:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDI Forwarder with Octave Shift")
        self.root.geometry("560x560")
        
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
        ttk.Label(parent, text="MIDI Channel:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.channel_var = tk.StringVar(value="Omni (0)")
        self.channel_dropdown = ttk.Combobox(parent, textvariable=self.channel_var, 
                                          values=["Omni (0)"] + [str(i) for i in range(1,17)])
        self.channel_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        
        # Octave shift slider
        ttk.Label(parent, text="Octave Shift:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.octave_slider = ttk.Scale(parent, from_=-4, to=6, orient='horizontal', 
                                     command=lambda v: self.set_octave_offset(int(float(v))))
        self.octave_slider.set(4)  # Default to octave 4
        self.octave_slider.grid(row=3, column=1, padx=5, pady=5, sticky='ew')
        ttk.Label(parent, text="(Shifts displayed octave range)").grid(row=4, column=1, sticky='w')
        
        # Control buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_forwarding)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_forwarding, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(parent, textvariable=self.status_var).grid(row=6, column=0, columnspan=2)
        
        # Message log
        log_frame = ttk.Frame(parent)
        log_frame.grid(row=7, column=0, columnspan=2, pady=5, sticky='ew')
        
        ttk.Label(log_frame, text="MIDI Messages:").pack(anchor='w')
        self.message_log = tk.Text(log_frame, height=4, width=60, state='disabled', bg='white', relief='sunken')
        self.message_log.pack(fill='x')
    
    def setup_piano(self, parent):
        """Setup piano keyboard visualization (fixed 2 octaves)"""
        self.piano_canvas = tk.Canvas(parent, bg='#f0f0f0', highlightthickness=0)
        self.piano_canvas.pack(fill='both', expand=True)
        self.draw_piano()
    
    def draw_piano(self):
        """Draw piano keys (always 2 octaves) with current octave offset"""
        self.piano_canvas.delete("all")
        self.keys = []
        
        key_width = 40
        key_height = 200
        black_width = key_width * 0.6
        black_height = key_height * 0.6
        
        # Draw white keys (2 octaves)
        for octave in range(2):
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
        
        # Draw black keys (2 octaves)
        for octave in range(2):
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
        self.status_var.set(f"Showing octaves {self.octave_offset+4}-{self.octave_offset+5}")
    
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
            # Set channel
            channel_str = self.channel_var.get()
            if channel_str == "Omni (0)":
                self.channel = None
                channel_display = "Omni"
            else:
                self.channel = int(channel_str) - 1
                channel_display = f"Ch {self.channel+1}"
            
            # Open ports
            self.input_port = mido.open_input(input_name)
            self.output_port = mido.open_output(output_name)
            self.running = True
            
            # Update UI
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.status_var.set(f"Forwarding {input_name} → {output_name} ({channel_display}) | Octaves {self.octave_offset+4}-{self.octave_offset+5}")
            
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
        self.status_var.set(f"Stopped | Octaves {self.octave_offset+4}-{self.octave_offset+5}")
    
    def forward_messages(self):
        """Forward MIDI messages in background"""
        while self.running:
            try:
                for msg in self.input_port.iter_pending():
                    # Process channel
                    if self.channel is not None and hasattr(msg, 'channel'):
                        msg.channel = self.channel
                    
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
            self.message_log.config(state='normal')
            self.message_log.insert('end', msg + '\n')
            
            # Keep last 3 messages
            lines = self.message_log.get('1.0', 'end').split('\n')
            if len(lines) > 4:
                self.message_log.delete('1.0', f"{len(lines)-4}.0")
            
            self.message_log.config(state='disabled')
            self.message_log.see('end')
        
        self.root.after(100, self.update_message_display)

if __name__ == "__main__":
    root = tk.Tk()
    app = MidiForwarderOctaveShift(root)
    root.mainloop()
