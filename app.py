import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import subprocess
import os
import spacy
import speech_recognition as sr
import threading 

PYTHON_SCRIPT_PATH = r"E:\levinproj\fetchlocation.py"
DIRECTIONS_FOLDER = os.path.join("dataset", "directions")
OBJECTS_FOLDER = os.path.join("dataset", "objects")

nlp = spacy.load("en_core_web_sm")

class ImageLayer:
    def __init__(self, name, image_path, canvas, layer_panel, x_position, y_position, resize_large=False):
        self.name = name
        self.image_path = image_path
        self.canvas = canvas
        self.layer_panel = layer_panel
        self.x_position = x_position
        self.y_position = y_position

        image_width = 1000 if resize_large else 100
        self.image = Image.open(image_path).resize((image_width, 100))
        self.tk_image = ImageTk.PhotoImage(self.image)

        self.canvas_id = self.canvas.create_image(self.x_position, self.y_position, image=self.tk_image)
        self.label_id = self.canvas.create_text(self.x_position, self.y_position + 60, text=self.name, fill="black")

        self.layer_frame = tk.Frame(layer_panel, bd=2, relief="solid", padx=10, pady=10)
        self.layer_frame.pack(pady=5, fill=tk.X, padx=5)

        tk.Label(self.layer_frame, text=self.name, font=("Helvetica", 14)).pack(side=tk.LEFT)
        close_button = tk.Button(self.layer_frame, text="Close", command=self.close_layer, font=("Helvetica", 12))
        close_button.pack(side=tk.RIGHT)

    def close_layer(self):
        self.canvas.delete(self.canvas_id)
        self.canvas.delete(self.label_id)
        self.layer_frame.destroy()

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Levin Alpha")
        self.root.geometry("1600x1000")  
        self.root.configure(bg="#FFDAB9")
        
        self.title_label = tk.Label(self.root, text="Levin Alpha Build v.1.0.21", font=("Helvetica", 20, "bold"), bg="#FFDAB9")
        self.title_label.grid(row=0, column=0, columnspan=3, pady=10, sticky="n")  

        self.canvas = tk.Canvas(root, width=1000, height=700, bg="white")
        self.canvas.grid(row=1, column=0, rowspan=2, padx=10, pady=10)

        self.button_frame = tk.Frame(self.root, bg="#FFDAB9")
        self.button_frame.grid(row=3, column=0, columnspan=2, pady=20) 

        self.record_button = tk.Button(
            self.button_frame,
            text="Record",
            command=self.start_recording,
            width=20,  
            height=3,  
            font=("Helvetica", 16)  
        )
        self.record_button.pack(side=tk.LEFT, padx=20)  

        self.stop_button = tk.Button(
            self.button_frame,
            text="Stop",
            command=self.stop_recording,
            width=20,
            height=3,
            font=("Helvetica", 16)
        )
        self.stop_button.pack(side=tk.LEFT, padx=20)
        self.stop_button.config(state=tk.DISABLED)

        self.layer_panel_container = tk.Frame(root, width=250, height=700, bg="#FFDAB9")
        self.layer_panel_container.grid(row=1, column=2, rowspan=2, padx=10, pady=10, sticky="n")
        self.layer_panel_container.grid_propagate(False)

        self.layer_panel = tk.Frame(self.layer_panel_container, bg="#FFDAB9")
        self.layer_panel.pack(fill=tk.BOTH, expand=True)

        self.layers_label = tk.Label(self.layer_panel, text="Layers:", font=("Helvetica", 16, "bold"), bg="#FFDAB9")
        self.layers_label.pack(pady=0)

        self.loaded_images = []
        self.recognizer = sr.Recognizer()
        self.audio_data = None

        self.notification_textbox = tk.Text(self.root, height=8, width=50,font=("Helvetica", 14))
        self.notification_textbox.grid(row=3, column=2, padx=10, pady=10)

    def start_recording(self):
        self.record_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        threading.Thread(target=self.record_audio).start()

    def record_audio(self):
        self.notification_textbox.delete(1.0, tk.END)
        self.notification_textbox.insert(tk.END, "Preparing ...\n")
        try:
            with sr.Microphone() as source:
                print("Microphone accessed. Adjusting for ambient noise...")
                self.notification_textbox.insert(tk.END, "Microphone accessed. Adjusting for ambient noise...\n")
                self.recognizer.adjust_for_ambient_noise(source)
                print("Listening for audio...")
                self.notification_textbox.insert(tk.END, "Speak Now...\n")
                self.audio_data = self.recognizer.listen(source)
                print("Audio data recorded.")
                self.notification_textbox.insert(tk.END, "Audio data recorded.\n")
        except Exception as e:
            print(f"Error during recording: {e}")
            self.notification_textbox.insert(tk.END, f"An error occurred while recording audio: {e}\n")
            self.reset_buttons()

    def stop_recording(self):
        self.record_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.audio_data is None:
            self.notification_textbox.insert(tk.END, "No audio data detected.\n")
            self.reset_buttons()
            return
        try:
            print("Converting audio to text...")
            input_text = self.recognizer.recognize_google(self.audio_data)
            self.notification_textbox.insert(tk.END, f"Transcribed text: {input_text}\n")
            self.generate_images(input_text)
        except sr.UnknownValueError:
            self.notification_textbox.insert(tk.END, "Google Speech Recognition could not understand audio.\n")
        except sr.RequestError as e:
            self.notification_textbox.insert(tk.END, f"Could not request results from Google Speech Recognition service; {e}\n")
        finally:
            self.reset_buttons()

    def reset_buttons(self):
        self.record_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def determine_positions(self, sentence):
        doc = nlp(sentence)
        positions = {}
        current_x1 = 150
        current_x2 = 1000-150
        static_x = 500
        current_y1 = 150
        current_y2 = 700-150
        static_y = 400
        below_y = static_y + 150
        is_below = False
        has_direction = False
        large_objects = set()
        direction_map = {
            "north": "north",
            "south": "south",
            "east": "east",
            "west": "west",
            "right": "right",
            "left": "left",
            "up": "up",
            "down": "down",
            "northeast": "northeast",
            "northwest": "northwest",
            "southeast": "southeast",
            "southwest": "southwest"
        }
        arrows = {}
        for i, token in enumerate(doc):
            word = token.text.lower()
            if token.pos_ == "NOUN":
                if i + 2 < len(doc) and doc[i + 2].text.lower() in ["left", "west"]:
                    positions[word] = (current_x2, static_y)
                    current_x2 -= 120
                elif i + 2 < len(doc) and doc[i + 2].text.lower() in ["up", "north"]:
                    positions[word] = (static_x, current_y2)
                    current_y2 -= 120
                elif i + 2 < len(doc) and doc[i + 2].text.lower() in ["down", "south"]:
                    positions[word] = (static_x, current_y1)
                    current_y1 += 120
                elif is_below:
                    positions[word] = (500, below_y)
                    below_y += 120
                    is_below = False
                    large_objects.add(word)
                else:
                    positions[word] = (current_x1, static_y)
                    current_x1 += 120
            elif token.pos_ == "ADP":
                if word in ["on"]:
                    is_below = True
            elif word in direction_map:
                if word in ["left", "west"]:
                    positions[word] = (current_x2, static_y)
                    arrows[word] = word
                    current_x2 -= 120
                    has_direction = True
                elif word in ["up", "north"]:
                    positions[word] = (static_x, current_y2)
                    arrows[word] = word
                    current_y2 -= 120
                    has_direction = True
                elif word in ["down", "south"]:
                    positions[word] = (static_x, current_y1)
                    arrows[word] = word
                    current_y1 += 120
                    has_direction = True
                else:
                    positions[word] = (current_x1, static_y)
                    arrows[word] = word
                    current_x1 += 120
                    has_direction = True

        if not has_direction:
            positions["right"] = (current_x1, static_y)
            current_x1 += 120

        return positions, large_objects, arrows

    def generate_images(self, input_text):
        if not input_text:
            messagebox.showwarning("Input Error", "Please enter a sentence!")
            return

        try:
            process = subprocess.Popen(
                ["python", PYTHON_SCRIPT_PATH, input_text],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if stderr:
                messagebox.showerror("Python Error", stderr)
                return

            self.canvas.delete("all")
            self.clear_layers()

            image_positions, large_objects, arrows = self.determine_positions(input_text)

            lines = stdout.splitlines()
            for line in lines:
                if " - " in line:
                    name, path = line.split(" - ")
                    if os.path.exists(path):
                        resize_large = name in large_objects
                        x, y = image_positions.get(name, (150, 100))
                        self.add_image_layer(name, path, x, y, resize_large)

                        if name in arrows:
                            direction = arrows[name]
                            arrow_image_path = os.path.join(DIRECTIONS_FOLDER, f"{direction}_arrow.png")
                            if os.path.exists(arrow_image_path):
                                self.add_image_layer(f"{direction}_arrow", arrow_image_path, x, y + 120)

            self.canvas.update()
            self.layer_panel.update()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while running the Python script: {e}")

    def add_image_layer(self, name, path, x, y, resize_large=False):
        image_layer = ImageLayer(name, path, self.canvas, self.layer_panel, x, y, resize_large)
        self.loaded_images.append(image_layer)

    def clear_layers(self):
        for layer in self.loaded_images:
            layer.layer_frame.destroy()
        self.loaded_images.clear()

if __name__ == "__main__":
    root = tk.Tk()
    root.state('zoomed')
    app = App(root)
    root.mainloop()