import tkinter as tk
from tkinter import filedialog
import main  # Importing the main.py code as a module

def browse_file():
    file_path = filedialog.askopenfilename(filetypes=[("Gcode Files", "*.gcode")])
    input_file_entry.delete(0, tk.END)
    input_file_entry.insert(0, file_path)

def analyze_file():
    input_file_path = input_file_entry.get()
    t_commands = main.get_t_commands(input_file_path)
    t_commands_listbox.delete(0, tk.END)  # Clear the listbox
    for idx, t_command in enumerate(t_commands, start=1):
        t_commands_listbox.insert(tk.END, f"{idx}. {t_command}")

def generate_swap():
    input_file_path = input_file_entry.get()
    selected_indices = t_commands_listbox.curselection()
    if len(selected_indices) != 2:
        swap_generated_label.config(text="Please select exactly two T commands.")
        return

    t_command1_idx, t_command2_idx = selected_indices
    t_command1 = t_commands_listbox.get(t_command1_idx).split(". ")[1]
    t_command2 = t_commands_listbox.get(t_command2_idx).split(". ")[1]
    main.generate_instructions(input_file_path, t_command1, t_command2)
    main.copy_features(input_file_path, t_command1, t_command2)
    swap_generated_label.config(text="Swap files generated successfully.")

def modify_gcode():
    input_file_path = input_file_entry.get()
    start_line = main.gcode_start_locator(input_file_path)
    calibration_start_line, calibration_end_line, calibration_extra_start, calibration_extra_end = main.turn_off_calibration(input_file_path, start_line)
    main.modify_gcode_cal(input_file_path, calibration_start_line, calibration_end_line, calibration_extra_start, calibration_extra_end)
    calibration_off_label.config(text="Calibration turned off successfully.")

def debug_output():
    input_file_path = input_file_entry.get()
    output_file_path_debug = input_file_path.replace(".gcode", "_debug.txt")
    main.write_to_output_file_debug(output_file_path_debug, input_file_path)
    debug_label.config(text="Debug file generated successfully.")


# Create the main window
root = tk.Tk()
root.title("Gcode Swap Generator")

# Input File Selection
input_file_label = tk.Label(root, text="Select Input File:")
input_file_label.grid(row=0, column=0, padx=10, pady=5)

input_file_entry = tk.Entry(root, width=50)
input_file_entry.grid(row=0, column=1, padx=5, pady=5)

browse_button = tk.Button(root, text="Browse", command=browse_file)
browse_button.grid(row=0, column=2, padx=5, pady=5)

# Analyze Input File
analyze_button = tk.Button(root, text="Analyze Input File", command=analyze_file)
analyze_button.grid(row=1, column=0, columnspan=3, padx=10, pady=5)

t_commands_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, width=50, height=10)
t_commands_listbox.grid(row=2, column=0, columnspan=3, padx=10, pady=5)

# Select T Commands
select_t_commands_label = tk.Label(root, text="Select Two T Commands to Swap:")
select_t_commands_label.grid(row=3, column=0, columnspan=3, padx=10, pady=5)

t_commands_listbox.grid(row=4, column=0, columnspan=3, padx=10, pady=5)

# Generate Swap
generate_swap_button = tk.Button(root, text="Generate Swap", command=generate_swap)
generate_swap_button.grid(row=5, column=0, columnspan=3, padx=10, pady=5)

swap_generated_label = tk.Label(root, text="")
swap_generated_label.grid(row=6, column=0, columnspan=3, padx=10, pady=5)

# Turn Calibration Off
calibration_off_button = tk.Button(root, text="Turn Calibration Off", command=modify_gcode)
calibration_off_button.grid(row=7, column=0, columnspan=3, padx=10, pady=5)

calibration_off_label = tk.Label(root, text="")
calibration_off_label.grid(row=8, column=0, columnspan=3, padx=10, pady=5)

# Debug Output
debug_button = tk.Button(root, text="Debug", command=debug_output)
debug_button.grid(row=9, column=0, columnspan=3, padx=10, pady=5)

debug_label = tk.Label(root, text="")
debug_label.grid(row=10, column=0, columnspan=3, padx=10, pady=5)

root.mainloop()
