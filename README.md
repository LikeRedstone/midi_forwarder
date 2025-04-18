# midi_forwarder
A small program that takes USB-MIDI from e.g. a Keyboard and forwards it through your PC to a Synthesizer.

## Features
- Real-time MIDI message forwarding
- Visible Notes with octave shifting
- Terminal with MIDI-data
  
## Requirements
- Python 3.x
- mido (`pip install mido`)
- python-rtmidi (`pip install python-rtmidi`)

## Installation
1. Clone this repository
2. Install requirements as mentioned

## Usage
Run directly:
```bash
python midi_forwarder.py
```

Or build executable:
```bash
pyinstaller --onefile midi_forwarder.py
```

## Configuration
Edit the script to:
- Change input/output ports
- Modify octave shift value
- Adjust other parameters

## Building for Distribution
```bash
pyinstaller --onefile --windowed midi_forwarder.py
```

The executable will be created in the `dist` folder.

## Additional notice
This build was created with the help of BLACKBOX AI (www.blackbox.ai). Other Librarys that are used but should come preinstalled on your python-build are tkinter, queue and threading.
