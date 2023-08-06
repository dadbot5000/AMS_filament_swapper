import re

def is_comment(line):
    # Check if the line is a comment (assuming comments start with a semicolon)
    return line.strip().startswith(";")

def gcode_start_locator(input_file_path):
    # Read the input G-code file and find the first command
    with open(input_file_path, "r") as input_file:
        lines = input_file.readlines()

        for i, line in enumerate(lines, start=1):
            # Skip empty lines and comments before finding the first command
            if not line.strip() or is_comment(line):
                continue

            # Find the first command and return its line number
            return i

    # Return None if no command is found
    return None

def gcode_command_locator(input_file_path, commands_to_find):
    # Initialize an empty dictionary to store the line numbers for each command
    command_line_numbers = {}

    # Read the input G-code file and find the line numbers for each command
    with open(input_file_path, "r") as input_file:
        for i, line in enumerate(input_file, start=1):
            # Skip lines that are comments
            if is_comment(line):
                continue

            for command in commands_to_find:
                if command.lower() in line.lower():  # Ignore case sensitivity
                    if command not in command_line_numbers:
                        command_line_numbers[command] = []
                    command_line_numbers[command].append(i)

    return command_line_numbers

def gcode_comments_locator(input_file_path, comments_to_find):
    # Initialize an empty dictionary to store the line numbers for each comment
    comment_line_numbers = {}

    # Read the input G-code file and find the line numbers for each comment
    with open(input_file_path, "r") as input_file:
        for i, line in enumerate(input_file, start=1):
            # Skip lines that are not comments
            if not is_comment(line):
                continue

            for comment in comments_to_find:
                if comment.lower() in line.lower():  # Ignore case sensitivity
                    if comment not in comment_line_numbers:
                        comment_line_numbers[comment] = []
                    comment_line_numbers[comment].append(i)

    return comment_line_numbers

def first_layer_end(input_file_path):
    # Find the line number for the comment "Z_HEIGHT: 0.4"
    comment_line_numbers = gcode_comments_locator(input_file_path, ["Z_HEIGHT: 0.4"])
    z_height_line = comment_line_numbers.get("Z_HEIGHT: 0.4", None)

    if z_height_line is not None:
        # Subtract 2 from the line number to get the "End of Layer 1 gcode" line number
        end_of_layer_line = z_height_line[0] - 2
        return end_of_layer_line

    # Return None if the "Z_HEIGHT: 0.4" comment is not found
    return None

def swap_finder(input_file_path):
    # Read the input G-code file and get the lines
    with open(input_file_path, "r") as input_file:
        lines = input_file.readlines()

    # Find the line numbers for the specified G-code commands
    commands_to_find = ["M620", "M621", "T"]
    command_line_numbers = gcode_command_locator(input_file_path, commands_to_find)

    # Create dictionaries to store start, middle, and end lines for each filament swap
    m620_swaps = {}
    m621_swaps = {}
    t_swaps = {}

    # Loop through the M620 commands and find associated M621 and T commands
    t_commands = command_line_numbers.get("T", [])
    m621_commands = command_line_numbers.get("M621", [])

    for m620_line in command_line_numbers.get("M620", []):
        m620_command = lines[m620_line - 1].strip()
        filament_number_match = re.search(r"S(\d+)A", m620_command)
        if filament_number_match:
            filament_number = int(filament_number_match.group(1))

            # Find the M621 command after the M620 command
            m621_line = next((line_num for line_num in m621_commands if line_num > m620_line), None)

            # Find the T command(s) between M620 and M621 commands
            t_lines = [line_num for line_num in t_commands if m620_line < line_num < m621_line]

            # Filter out T commands that are part of other commands (e.g., "T1" within "T10")
            t_lines = [line_num for line_num in t_lines if lines[line_num - 1].strip() == f"T{filament_number}"]

            # Add the swap data to the appropriate dictionary
            if m620_line not in m620_swaps:
                m620_swaps[m620_line] = {"start": [m620_line], "middle": t_lines, "end": [m621_line]}
            else:
                m620_swaps[m620_line]["middle"].extend(t_lines)

            # Add the T command(s) to the t_swaps dictionary
            for t_line in t_lines:
                t_swaps[t_line] = {"start": [], "middle": [t_line], "end": []}

    # Loop through the M621 commands and find associated M620 commands
    for m621_line in command_line_numbers.get("M621", []):
        # Find the M620 command closest to the M621 command without exceeding it
        m620_line = next((line_num for line_num in command_line_numbers.get("M620", []) if line_num < m621_line), None)

        # Add the swap data to the m621_swaps dictionary
        m621_swaps[m621_line] = {"start": [m620_line], "middle": [], "end": [m621_line]}

    # Loop through the T commands and find associated M620 and M621 commands
    for t_line in command_line_numbers.get("T", []):
        # Find the M620 command before the T command
        m620_line = next((line_num for line_num in command_line_numbers.get("M620", []) if line_num < t_line), None)

        # Find the M621 command after the T command
        m621_line = next((line_num for line_num in command_line_numbers.get("M621", []) if line_num > t_line), None)

        # Add the swap data to the t_swaps dictionary
        t_swaps[t_line] = {"start": [m620_line], "middle": [t_line], "end": [m621_line]}

    return m620_swaps, m621_swaps, t_swaps

def swap_finder_fixer(input_file_path, m620_swaps):
    # Read the input G-code file and get the lines
    with open(input_file_path, "r") as input_file:
        lines = input_file.readlines()

    # Create a list to store the corrected filament swaps
    corrected_swaps_list = []

    for swap_line, swap_data in m620_swaps.items():
        # Find the M620 command at the specified line
        m620_command = lines[swap_line - 1].strip()

        # Extract the filament number from the M620 command
        filament_number_match = re.search(r"S(\d+)A", m620_command)
        if filament_number_match:
            filament_number = int(filament_number_match.group(1))

            # Find the M621 command after the M620 command
            m621_line = swap_data["end"][0] if swap_data["end"] else None

            # Find the T commands between M620 and M621 commands
            t_lines = []
            if m621_line:
                for t_line in range(swap_line + 1, m621_line):
                    t_command = lines[t_line - 1].strip()
                    t_filament_number_match = re.search(r"T(\d+)", t_command)
                    if t_filament_number_match and int(t_filament_number_match.group(1)) == filament_number:
                        t_lines.append(t_line)

            # Add the corrected swap data to the list
            corrected_swap_data = {
                "filament_number": filament_number,
                "start_lines": swap_data["start"],
                "middle_lines": t_lines,
                "end_lines": swap_data["end"]
            }
            corrected_swaps_list.append(corrected_swap_data)

    return corrected_swaps_list

def filter_output(output_data, start_line, end_line):
    # Handle dictionaries, lists, and simple lists of line numbers
    if isinstance(output_data, dict):
        filtered_output = {}
        for item, line_numbers in output_data.items():
            filtered_lines = [line for line in line_numbers if start_line <= line <= end_line]
            if filtered_lines:
                filtered_output[item] = filtered_lines
    elif isinstance(output_data, list):
        filtered_output = [line for line in output_data if start_line <= line <= end_line]
    else:
        filtered_output = None

    return filtered_output

def feature_start_finder(input_file_path):
    # Read the input G-code file and get the lines
    with open(input_file_path, "r") as input_file:
        lines = input_file.readlines()

    # Find the line numbers for the "CP TOOLCHANGE END" comment
    toolchange_comments = gcode_comments_locator(input_file_path, ["CP TOOLCHANGE END"])

    # Initialize a dictionary to store the feature start line for each toolchange
    feature_start_lines = {}

    # Find the first instance of "G1 E-.8 F1800" in the entire file
    for i, line in enumerate(lines, start=1):
        if "G1 E-.8 F1800" in line:
            feature_start_lines["G1 E-.8 F1800"] = i + 1
            break

    # Find the first instance of "G1 E-.04 F1800" after each "CP TOOLCHANGE END" comment
    for toolchange_line in toolchange_comments.get("CP TOOLCHANGE END", []):
        for i in range(toolchange_line + 1, len(lines)):
            line = lines[i]
            if "G1 E-.04 F1800" in line:
                feature_start_lines[toolchange_line] = i + 4
                break

    # Return only the feature start lines without the toolchange lines
    return list(feature_start_lines.values())

def feature_identifier(input_file_path):
    # Read the input G-code file and get the lines
    with open(input_file_path, "r") as input_file:
        lines = input_file.readlines()

    # Find the feature start lines for each "CP TOOLCHANGE END" comment
    feature_start_lines = feature_start_finder(input_file_path)

    # Initialize a dictionary to store the identified Ti commands for each feature start line
    ti_commands = {}

    # Find the first instance of a "Ti" command preceding each feature start line
    for feature_start_line in feature_start_lines:
        # Search for the first instance of a "Ti" command before the feature start line
        ti_command_line = None
        for i in range(feature_start_line - 1, 0, -1):
            line = lines[i].strip()
            if line.startswith("T") and line[1:].isdigit():
                ti_command_line = i + 1
                break

        # Add the identified Ti command to the dictionary
        if ti_command_line:
            ti_command = lines[ti_command_line - 1].strip()
            ti_commands[feature_start_line] = ti_command
        else:
            ti_commands[feature_start_line] = None

    return ti_commands

def find_wipe_start_end(input_file_path):
    # Find the line numbers for the "CP TOOLCHANGE START" comment
    toolchange_start_comments = gcode_comments_locator(input_file_path, ["CP TOOLCHANGE START"])

    # Initialize a dictionary to store the wipe start and end line for each toolchange
    wipe_start_end_lines = {}

    # Find the first instance of "WIPE_START" after each "CP TOOLCHANGE START" comment
    for toolchange_line in toolchange_start_comments.get("CP TOOLCHANGE START", []):
        with open(input_file_path, "r") as input_file:
            lines = input_file.readlines()

        for i in range(toolchange_line + 1, len(lines)):
            line = lines[i]
            if "WIPE_START" in line:
                wipe_start_end_lines[toolchange_line] = {"wipe_start": i}
                break

    # Find the first instance of "WIPE_END" after each "WIPE_START" comment
    for toolchange_line, wipe_data in wipe_start_end_lines.items():
        wipe_start_line = wipe_data["wipe_start"]
        with open(input_file_path, "r") as input_file:
            lines = input_file.readlines()

        for i in range(wipe_start_line + 1, len(lines)):
            line = lines[i]
            if "WIPE_END" in line:
                wipe_start_end_lines[toolchange_line]["wipe_end"] = i
                break
    
    return wipe_start_end_lines

def wipe_identifier(input_file_path, filtered_wipe_start_end_lines):
    # Initialize a dictionary to store the corresponding "T" command for each wipe start line
    wipe_ti_commands = {}

    # Read the input G-code file and get the lines
    with open(input_file_path, "r") as input_file:
        lines = input_file.readlines()

        # Fetch the corresponding "T" command for each wipe start line from the G-code file content
        for wipe_data in filtered_wipe_start_end_lines.values():
            wipe_start_line = wipe_data.get("wipe_start", None)
            if wipe_start_line:
                for i in range(wipe_start_line - 1, 0, -1):
                    line = lines[i].strip()
                    if line.startswith("T") and line[1:].isdigit():
                        wipe_ti_commands[wipe_start_line] = line
                        break
    
    return wipe_ti_commands

def turn_off_calibration(input_file_path, start_line):
    # Define the comments to find
    calibration_start_comment = "extrinsic para cali paint"
    calibration_end_comment = "turn off light and wait extrude temperature"

    # Find the line numbers for the specified comments starting from 'start_line'
    comment_line_numbers = gcode_comments_locator(input_file_path, [calibration_start_comment, calibration_end_comment])

    # Find the line number for the "extrinsic para cali paint" comment that comes after 'start_line'
    calibration_start_line = next((line for line in comment_line_numbers.get(calibration_start_comment, []) if line >= start_line), None)

    # Find the line number for the "turn off light and wait extrude temperature" comment that comes after 'start_line'
    calibration_end_line = next((line for line in comment_line_numbers.get(calibration_end_comment, []) if line >= start_line), None)

    if calibration_start_line is not None and calibration_end_line is not None:
        # Calculate Calibration_extra_start and Calibration_extra_end
        calibration_extra_start = calibration_end_line + 2
        calibration_extra_end = calibration_extra_start + 5

        return calibration_start_line, calibration_end_line, calibration_extra_start, calibration_extra_end
    else:
        return None, None, None, None
    
def modify_gcode_cal(input_file_path, calibration_start, calibration_end, calibration_extra_start, calibration_extra_end):
    # Create the output file name by appending "_output" at the end of the input file name
    output_file_name = input_file_path.split(".")[0] + "_cal_off_output.gcode"

    # Read the content of the input file
    with open(input_file_path, "r") as input_file:
        gcode_lines = input_file.readlines()

    # Modify the G-code lines based on the provided calibration ranges
    for line_number in range(calibration_start, calibration_end + 1):
        if line_number <= len(gcode_lines):  # Ensure line number is within the range
            gcode_lines[line_number - 1] = ";" + gcode_lines[line_number - 1]

    for line_number in range(calibration_extra_start, calibration_extra_end + 1):
        if line_number <= len(gcode_lines):  # Ensure line number is within the range
            gcode_lines[line_number - 1] = ";" + gcode_lines[line_number - 1]

    # Write the modified G-code lines to the output file
    with open(output_file_name, "w") as output_file:
        output_file.writelines(gcode_lines)

    # Print a console message indicating the output file name
    #print(f"Output G-code file written to '{output_file_name}'.")

def feature_locator_wformat(input_file_path):
    # Find the feature start lines for each "CP TOOLCHANGE END" comment
    feature_start_lines = feature_start_finder(input_file_path)

    # Find the associated T commands for each feature start line
    ti_commands = feature_identifier(input_file_path)

    # Initialize lists to store the feature information
    feature_info_list = []

    # Find the feature start lines and corresponding T commands
    for start_line in feature_start_lines:
        # Find the corresponding T command for the feature start line
        t_cmd = ti_commands.get(start_line, None)

        # Find the feature end line as the line before "CP TOOLCHANGE START" comment
        toolchange_start_comments = gcode_comments_locator(input_file_path, ["CP TOOLCHANGE START"])
        feature_end_line = next((line - 5 for line in toolchange_start_comments.get("CP TOOLCHANGE START", []) if line > start_line), None)

        if t_cmd is not None and feature_end_line is not None:
            feature_info = {
                "start_line": start_line,
                "end_line": feature_end_line,
                "t_command": t_cmd
            }
            feature_info_list.append(feature_info)

    # Filter the feature_info_list based on the start_line
    filtered_feature_info_list = [info for info in feature_info_list if info["start_line"] <= first_layer_end(input_file_path)]
    filtered_feature_info_list_2 = [info for info in filtered_feature_info_list if info["end_line"] <= first_layer_end(input_file_path)]

    return filtered_feature_info_list_2

def copy_features(input_file_path, t_command1, t_command2):
    # Create a new output file name
    output_file_path = input_file_path.replace(".gcode", "_features.gcode")

    # Find the line number for the "Start of Layer 1 gcode"
    start_line = gcode_start_locator(input_file_path)

    # Find the line number for the "End of Layer 1 gcode"
    end_line = first_layer_end(input_file_path)

    # Find the feature locations and associated T commands
    feature_info_list = feature_locator_wformat(input_file_path)

    # Find the corresponding start_line and end_line for the first T command
    start_line_t1 = None
    end_line_t1 = None
    for feature_info in feature_info_list:
        if feature_info["t_command"] == t_command1:
            start_line_t1 = feature_info["start_line"]
            end_line_t1 = feature_info["end_line"]
            break

    if start_line_t1 is None or end_line_t1 is None:
        print(f"No features found for T command '{t_command1}'.")
        return
    
    # Find the corresponding start_line and end_line for the second T command
    start_line_t2 = None
    end_line_t2 = None
    for feature_info in feature_info_list:
        if feature_info["t_command"] == t_command2:
            start_line_t2 = feature_info["start_line"]
            end_line_t2 = feature_info["end_line"]
            break

    if start_line_t2 is None or end_line_t2 is None:
        print(f"No features found for T command '{t_command2}'.")
        return
    
     # Find the wipe start and end lines for each "CP TOOLCHANGE START" comment
    wipe_start_end_lines = find_wipe_start_end(input_file_path)

    # Filter the wipe start and end lines based on start_line and end_line
    filtered_wipe_start_end_lines = {}
    for toolchange_line, wipe_data in wipe_start_end_lines.items():
        wipe_start_line = wipe_data.get("wipe_start", None)
        wipe_end_line = wipe_data.get("wipe_end", None)
        if wipe_start_line is not None and wipe_end_line is not None:
            if start_line <= wipe_start_line <= end_line or start_line <= wipe_end_line <= end_line:
                filtered_wipe_start_end_lines[toolchange_line] = {"wipe_start": wipe_start_line, "wipe_end": wipe_end_line}

    # Identify the "T" command for each wipe start line
    wipe_ti_commands = wipe_identifier(input_file_path, filtered_wipe_start_end_lines)
    filtered_wipes = {value['wipe_start']: {'wipe_end': value['wipe_end']} for value in filtered_wipe_start_end_lines.values()}
    wipe_commands_joined = {key: {'tool': value, 'wipe_end': filtered_wipes[key]['wipe_end']} for key, value in wipe_ti_commands.items()}
    wipe_commands = {value['tool']: {'wipe_start': key, 'wipe_end': value['wipe_end']} for key, value in wipe_commands_joined.items()}


    # Copy the lines for the first T command to the new output file
    with open(input_file_path, "r") as input_file, open(output_file_path, "w") as output_file:
        lines = input_file.readlines()
        copying_t1 = False
        for i, line in enumerate(lines, 1):
            if i == start_line_t1:
                output_file.write(f"; Start of Feature {t_command1}\n")
                copying_t1 = True
            if copying_t1:
                output_file.write(line)
            if i == end_line_t1:
                output_file.write(f"; End of Feature {t_command1}\n")
                break
    
    # Copy the lines for the T command wipe to the output file (append mode)
    with open(output_file_path, "a") as output_file:
        output_file.write(f"\n; Start of Wipe {t_command1}\n")
        for i, line in enumerate(lines, 1):
            if i >= wipe_commands[t_command1]['wipe_start'] + 1:
                output_file.write(line)
            if i == wipe_commands[t_command1]['wipe_end'] + 1:
                output_file.write(f"; End of Wipe {t_command1}\n")
                break

    # Copy the lines for the second T command to the output file (append mode)
    with open(output_file_path, "a") as output_file:
        output_file.write(f"\n; Start of Feature {t_command2}\n")
        for i, line in enumerate(lines, 1):
            if i >= start_line_t2:
                output_file.write(line)
            if i == end_line_t2:
                output_file.write(f"; End of Feature {t_command2}\n")
                break

    # Copy the lines for the T command wipe to the output file (append mode)
    with open(output_file_path, "a") as output_file:
        output_file.write(f"\n; Start of Wipe {t_command2}\n")
        for i, line in enumerate(lines, 1):
            if i >= wipe_commands[t_command2]['wipe_start'] + 1:
                output_file.write(line)
            if i == wipe_commands[t_command2]['wipe_end'] + 1:
                output_file.write(f"; End of Wipe {t_command2}\n")
                break
    return(output_file_path)
    #print(f"Feature lines copied successfully to '{output_file_path}'")

def write_to_output_file_debug(output_file_path, input_file_path):
    # Find the line number for the "Start of Layer 1 gcode"
    start_line = gcode_start_locator(input_file_path)

    # Find the line number for the "End of Layer 1 gcode"
    end_line = first_layer_end(input_file_path)

    # Find the feature start lines for each "CP TOOLCHANGE END" comment
    feature_start_lines = feature_start_finder(input_file_path)

    # Find the line numbers for the specified G-code commands
    commands_to_find = ["M620 S",
                        "M621"]
    command_line_numbers = gcode_command_locator(input_file_path, commands_to_find)

    # Find the line numbers for the specified comments
    comments_to_find = ["extrinsic para cali paint", 
                        "light and wait extrude temperature",
                        "CP TOOLCHANGE START"]
    comment_line_numbers = gcode_comments_locator(input_file_path, comments_to_find)

    # Filter the output data based on start_line and end_line
    filtered_command_line_numbers = filter_output(command_line_numbers, start_line, end_line)
    filtered_comment_line_numbers = filter_output(comment_line_numbers, start_line, end_line)
    filtered_feature_start_lines = filter_output(feature_start_lines, start_line, end_line)

    # Find the line numbers for the filament swaps "M620 SiA", "M621 SiA", and "T0-T7"
    m620_swaps, m621_swaps, t_swaps = swap_finder(input_file_path)
    # Fix the filament numbers and get the corrected swaps list
    corrected_swaps_list = swap_finder_fixer(input_file_path, m620_swaps)

    # Identify the Ti commands for each feature start line
    ti_commands = feature_identifier(input_file_path)

    # Find the "Feature End Lines" as the line before "CP TOOLCHANGE START" comment
    toolchange_start_comments = gcode_comments_locator(input_file_path, ["CP TOOLCHANGE START"])
    feature_end_lines = [line - 5 for line in toolchange_start_comments.get("CP TOOLCHANGE START", [])]

    # Filter the feature end lines based on start_line and end_line
    filtered_feature_end_lines = [line for line in feature_end_lines if start_line <= line <= end_line]
    # Add the "End of Layer 1 gcode" line to the end of the filtered_feature_end_lines list
    if end_line is not None:
        filtered_feature_end_lines.append(end_line)

    # Find the wipe start and end lines for each "CP TOOLCHANGE START" comment
    wipe_start_end_lines = find_wipe_start_end(input_file_path)

    # Filter the wipe start and end lines based on start_line and end_line
    filtered_wipe_start_end_lines = {}
    for toolchange_line, wipe_data in wipe_start_end_lines.items():
        wipe_start_line = wipe_data.get("wipe_start", None)
        wipe_end_line = wipe_data.get("wipe_end", None)
        if wipe_start_line is not None and wipe_end_line is not None:
            if start_line <= wipe_start_line <= end_line or start_line <= wipe_end_line <= end_line:
                filtered_wipe_start_end_lines[toolchange_line] = {"wipe_start": wipe_start_line, "wipe_end": wipe_end_line}

    # Identify the "T" command for each wipe start line
    wipe_ti_commands = wipe_identifier(input_file_path, filtered_wipe_start_end_lines)

    # Write the results to the output file
    with open(output_file_path, "w") as output_file:
        # Write G-code commands
        output_file.write("G-code commands:\n")
        for command, line_numbers in filtered_command_line_numbers.items():
            output_file.write(f"Found command '{command}' at line(s): {', '.join(map(str, line_numbers))}\n")

        # Write comments
        output_file.write("\nComments:\n")
        for comment, line_numbers in filtered_comment_line_numbers.items():
            output_file.write(f"Found comment '{comment}' at line(s): {', '.join(map(str, line_numbers))}\n")

        # Write Start of Layer 1 gcode
        output_file.write("\nStart of Layer 1 gcode:\n")
        output_file.write(f"{start_line}\n")

        # Write End of Layer 1 gcode
        output_file.write("\nEnd of Layer 1 gcode:\n")
        if end_line is not None:
            output_file.write(f"{end_line}\n")
        else:
            output_file.write("End of Layer 1 gcode not found.\n")
        
        # Write the filament swaps to the output file under the "Filament Swaps" section
        output_file.write("\nFilament Swaps:\n")
        for swap_count, swap_data in enumerate(corrected_swaps_list, start=1):
            filament_number = swap_data["filament_number"]
            start_lines = filter_output(swap_data["start_lines"], start_line, end_line)
            middle_lines = filter_output(swap_data["middle_lines"], start_line, end_line)
            end_lines = filter_output(swap_data["end_lines"], start_line, end_line)

            if not start_lines and not middle_lines and not end_lines:
                continue  # Skip swaps that are outside the filtered range

            output_file.write(f"\nFilament Swap {swap_count}\n")
            if start_lines:
                output_file.write(f"M620 S{filament_number}A (Start) at line(s): {', '.join(map(str, start_lines))}\n")
            if middle_lines:
                output_file.write(f"T{filament_number} (Middle) at line(s): {', '.join(map(str, middle_lines))}\n")
            if end_lines:
                output_file.write(f"M621 S{filament_number}A (End) at line(s): {', '.join(map(str, end_lines))}\n")
        
        # Write the feature start and end lines with identified Ti commands to the output file under the "Feature Locations" section
        output_file.write("\nFeature Locations:\n")
        for feature_start_line in filtered_feature_start_lines:
            ti_command = ti_commands.get(feature_start_line, None)
            if ti_command:
                feature_end_line = next((line for line in filtered_feature_end_lines if line > feature_start_line), None)
                output_file.write(f"{ti_command} starts at line {feature_start_line} and ends at line {feature_end_line}\n")
            else:
                output_file.write(f"Ti command not found for feature start line {feature_start_line}\n")
        
        # Write the filtered wipe start and end lines for each "CP TOOLCHANGE START" comment to the output file under the "Wipe Locations" section
        output_file.write("\nWipe Locations:\n")
        for wipe_data in filtered_wipe_start_end_lines.values():
            wipe_start_line = wipe_data.get("wipe_start", None)
            wipe_end_line = wipe_data.get("wipe_end", None)
            if wipe_start_line is not None and wipe_end_line is not None:
                # Fetch the corresponding "T" command for the wipe start line from the wipe_ti_commands dictionary
                ti_command = wipe_ti_commands.get(wipe_start_line, None)
                output_file.write(f"{ti_command} Wipe starts at line {wipe_start_line} and ends at line {wipe_end_line}\n")

def generate_instructions(input_file_path, t_command1, t_command2):
    # Create the output file name
    output_file_path = input_file_path.split(".")[0] + "_instructions.txt"

    # Extract the numeric part from t_command1 and t_command2
    t_command1_num = int(t_command1[1:])
    t_command2_num = int(t_command2[1:])

    # Find the line number for the "Start of Layer 1 gcode"
    start_line = gcode_start_locator(input_file_path)
   
    # Find the line number for the "End of Layer 1 gcode"
    end_line = first_layer_end(input_file_path)
   
    # Find the feature start lines for each "CP TOOLCHANGE END" comment
    feature_start_lines = feature_start_finder(input_file_path)
    filtered_feature_start_lines = filter_output(feature_start_lines, start_line, end_line)

    # Find the "Feature End Lines" as the line before "CP TOOLCHANGE START" comment
    toolchange_start_comments = gcode_comments_locator(input_file_path, ["CP TOOLCHANGE START"])
    feature_end_lines = [line - 5 for line in toolchange_start_comments.get("CP TOOLCHANGE START", [])]
    
    # Filter the feature end lines based on start_line and end_line
    filtered_feature_end_lines = [line for line in feature_end_lines if start_line <= line <= end_line]
    
    # Add the "End of Layer 1 gcode" line to the end of the filtered_feature_end_lines list
    if end_line is not None:
        filtered_feature_end_lines.append(end_line)

    # Identify the Ti commands for each feature start line
    ti_commands = feature_identifier(input_file_path)

    # Find the wipe start and end lines for each "CP TOOLCHANGE START" comment
    wipe_start_end_lines = find_wipe_start_end(input_file_path)

    # Filter the wipe start and end lines based on start_line and end_line
    filtered_wipe_start_end_lines = {}
    for toolchange_line, wipe_data in wipe_start_end_lines.items():
        wipe_start_line = wipe_data.get("wipe_start", None)
        wipe_end_line = wipe_data.get("wipe_end", None)
        if wipe_start_line is not None and wipe_end_line is not None:
            if start_line <= wipe_start_line <= end_line or start_line <= wipe_end_line <= end_line:
                filtered_wipe_start_end_lines[toolchange_line] = {"wipe_start": wipe_start_line, "wipe_end": wipe_end_line}

    # Identify the "T" command for each wipe start line
    wipe_ti_commands = wipe_identifier(input_file_path, filtered_wipe_start_end_lines)
    # Find the line numbers for the filament swaps "M620 SiA", "M621 SiA", and "T0-T7"
    m620_swaps, m621_swaps, t_swaps = swap_finder(input_file_path)
    # Fix the filament numbers and get the corrected swaps list
    corrected_swaps_list = swap_finder_fixer(input_file_path, m620_swaps)
    
    # Generate the content for the instructions file
    content = (
        "Use these instructions at your own risk. These were developed with very specific needs for my own setup, and may damage your printer.\n\n"
        f"Selected Filament Swaps: {t_command1} <-> {t_command2}\n"
    )

    # Write the content to the output file
    with open(output_file_path, "w") as output_file:
        output_file.write(content)
        
        # Write Start of Layer 1 gcode
        output_file.write("\nStart of Layer 1 gcode:\n")
        output_file.write(f"{start_line}\n")

        # Write End of Layer 1 gcode
        output_file.write("\nEnd of Layer 1 gcode:\n")
        output_file.write(f"{end_line}\n")

        # Write more instructions
        output_file.write("\nYou need to edit the number value in each of the Filament Swaps below\n")

        output_file.write("\nFilament Swaps:\n")
        swap_count = 1
        for swap_data in corrected_swaps_list:
            filament_number = swap_data["filament_number"]
            if filament_number == t_command1_num or filament_number == t_command2_num:
                start_lines = filter_output(swap_data["start_lines"], start_line, end_line)
                middle_lines = filter_output(swap_data["middle_lines"], start_line, end_line)
                end_lines = filter_output(swap_data["end_lines"], start_line, end_line)

                if not start_lines and not middle_lines and not end_lines:
                    continue  # Skip swaps that are outside the filtered range

                if start_lines:
                    output_file.write(f"M620 S{filament_number}A (Start) at line(s): {', '.join(map(str, start_lines))}\n")
                if middle_lines:
                    output_file.write(f"T{filament_number} (Middle) at line(s): {', '.join(map(str, middle_lines))}\n")
                if end_lines:
                    output_file.write(f"M621 S{filament_number}A (End) at line(s): {', '.join(map(str, end_lines))}\n")
                output_file.write("\n")
                swap_count += 1

        # Write more instructions
        output_file.write(
            "\nYou need to swap the corresponding feature and wipe sections.\n"
            f"These are marked in the output gcode file and pasted in the features output file.\n"
            f"Remember! The line numbers will change after you make your first paste. Start from the bottom and work your way up.\n"
            f"The locations in the input file are noted below.\n"
        )

        # Write the feature start and end lines with identified Ti commands to the output file under the "Feature Locations" section
        output_file.write("\nFeature Locations:\n")
        for feature_start_line in filtered_feature_start_lines:
            ti_command = ti_commands.get(feature_start_line, None)
            if ti_command and (ti_command == t_command1 or ti_command == t_command2):
                feature_end_line = next((line for line in filtered_feature_end_lines if line > feature_start_line), None)
                output_file.write(f"{ti_command} starts at line {feature_start_line} and ends at line {feature_end_line}\n")

        # Write the filtered wipe start and end lines for each "CP TOOLCHANGE START" comment to the output file under the "Wipe Locations" section
        output_file.write("\nWipe Locations:\n")
        for wipe_data in filtered_wipe_start_end_lines.values():
            wipe_start_line = wipe_data.get("wipe_start", None)
            wipe_end_line = wipe_data.get("wipe_end", None)
            if wipe_start_line is not None and wipe_end_line is not None:
                # Fetch the corresponding "T" command for the wipe start line from the wipe_ti_commands dictionary
                ti_command = wipe_ti_commands.get(wipe_start_line, None)
                if ti_command and (ti_command == t_command1 or ti_command == t_command2):
                    output_file.write(f"{ti_command} Wipe starts at line {wipe_start_line} and ends at line {wipe_end_line}\n")


    #print(f"Instructions written to '{output_file_path}'.")

def comment_feat_wipe(input_file_path, t_command1, t_command2):
    # Create the output file name
    output_file_path = input_file_path.replace(".gcode", "_feature_comments.gcode")

    # Extract the numeric part from t_command1 and t_command2
    t_command1_num = int(t_command1[1:])
    t_command2_num = int(t_command2[1:])

    # Find the line number for the "Start of Layer 1 gcode"
    start_line = gcode_start_locator(input_file_path)
   
    # Find the line number for the "End of Layer 1 gcode"
    end_line = first_layer_end(input_file_path)
   
    # Find the feature start lines for each "CP TOOLCHANGE END" comment
    feature_start_lines = feature_start_finder(input_file_path)
    filtered_feature_start_lines = filter_output(feature_start_lines, start_line, end_line)

    # Find the "Feature End Lines" as the line before "CP TOOLCHANGE START" comment
    toolchange_start_comments = gcode_comments_locator(input_file_path, ["CP TOOLCHANGE START"])
    feature_end_lines = [line - 5 for line in toolchange_start_comments.get("CP TOOLCHANGE START", [])]
    
    # Filter the feature end lines based on start_line and end_line
    filtered_feature_end_lines = [line for line in feature_end_lines if start_line <= line <= end_line]
    # Add the "End of Layer 1 gcode" line to the end of the filtered_feature_end_lines list
    if end_line is not None:
        filtered_feature_end_lines.append(end_line)

    # Identify the Ti commands for each feature start line
    ti_commands = feature_identifier(input_file_path)
    #print(ti_commands)

    # Find the wipe start and end lines for each "CP TOOLCHANGE START" comment
    wipe_start_end_lines = find_wipe_start_end(input_file_path)

    # Filter the wipe start and end lines based on start_line and end_line
    filtered_wipe_start_end_lines = {}
    for toolchange_line, wipe_data in wipe_start_end_lines.items():
        wipe_start_line = wipe_data.get("wipe_start", None)
        wipe_end_line = wipe_data.get("wipe_end", None)
        if wipe_start_line is not None and wipe_end_line is not None:
            if start_line <= wipe_start_line <= end_line or start_line <= wipe_end_line <= end_line:
                filtered_wipe_start_end_lines[toolchange_line] = {"wipe_start": wipe_start_line, "wipe_end": wipe_end_line}
   
    # Identify the "T" command for each wipe start line
    wipe_ti_commands = wipe_identifier(input_file_path, filtered_wipe_start_end_lines)

    # Store the feature start and end lines for t_command1
    t_command1_feature_lines = []
    for feature_start_line in filtered_feature_start_lines:
        ti_command = ti_commands.get(feature_start_line, None)
        if ti_command and int(ti_command[1:]) == t_command1_num:
            feature_end_line = next((line for line in filtered_feature_end_lines if line > feature_start_line), None)
            t_command1_feature_lines.append((feature_start_line, feature_end_line))
    
    t_command2_feature_lines = []
    for feature_start_line in filtered_feature_start_lines:
        ti_command = ti_commands.get(feature_start_line, None)
        if ti_command and int(ti_command[1:]) == t_command2_num:
            feature_end_line = next((line for line in filtered_feature_end_lines if line > feature_start_line), None)
            t_command2_feature_lines.append((feature_start_line, feature_end_line))
    
    # Store the wipe start and end lines for t_command1
    t_command2_wipe_lines = []
    for wipe_data in filtered_wipe_start_end_lines.values():
            wipe_start_line = wipe_data.get("wipe_start", None)
            wipe_end_line = wipe_data.get("wipe_end", None)
            if wipe_start_line is not None and wipe_end_line is not None:
                # Fetch the corresponding "T" command for the wipe start line from the wipe_ti_commands dictionary
                ti_command = wipe_ti_commands.get(wipe_start_line, None)
                if ti_command and (ti_command == t_command2):
                    t_command2_wipe_lines.append((wipe_start_line, wipe_end_line))
    
    t_command1_wipe_lines = []
    for wipe_data in filtered_wipe_start_end_lines.values():
            wipe_start_line = wipe_data.get("wipe_start", None)
            wipe_end_line = wipe_data.get("wipe_end", None)
            if wipe_start_line is not None and wipe_end_line is not None:
                # Fetch the corresponding "T" command for the wipe start line from the wipe_ti_commands dictionary
                ti_command = wipe_ti_commands.get(wipe_start_line, None)
                if ti_command and (ti_command == t_command1):
                    t_command1_wipe_lines.append((wipe_start_line, wipe_end_line))

    # Read the content of the input gcode file
    with open(input_file_path, "r") as input_file:
        gcode_content = input_file.readlines()

    # Add the comments
        first_line = t_command1_feature_lines[0][0]
        gcode_content[first_line - 1] = gcode_content[first_line - 1].rstrip() + f"; T{t_command1_num} FEATURE START\n"

        second_line = t_command1_feature_lines[0][1]
        gcode_content[second_line - 1] = gcode_content[second_line - 1].rstrip() + f"; T{t_command1_num} FEATURE END\n"

        first_line_2 = t_command2_feature_lines[0][0]
        gcode_content[first_line_2 - 1] = gcode_content[first_line_2 - 1].rstrip() + f"; T{t_command2_num} FEATURE START\n"

        second_line_2 = t_command2_feature_lines[0][1]
        gcode_content[second_line_2 - 1] = gcode_content[second_line_2 - 1].rstrip() + f"; T{t_command2_num} FEATURE END\n"
    
        first_line_wipe1 = t_command1_wipe_lines[0][0]
        gcode_content[first_line_wipe1] = gcode_content[first_line_wipe1].rstrip() + f"; T{t_command1_num} FEATURE WIPE START\n"

        second_line_wipe1 = t_command1_wipe_lines[0][1]
        gcode_content[second_line_wipe1] = gcode_content[second_line_wipe1].rstrip() + f"; T{t_command1_num} FEATURE WIPE END\n"

        first_line_wipe2 = t_command2_wipe_lines[0][0]
        gcode_content[first_line_wipe2] = gcode_content[first_line_wipe2].rstrip() + f"; T{t_command2_num} FEATURE WIPE START\n"

        second_line_wipe2 = t_command2_wipe_lines[0][1]
        gcode_content[second_line_wipe2] = gcode_content[second_line_wipe2].rstrip() + f"; T{t_command2_num} FEATURE WIPE END\n"

    # Write the updated content to the output file
    with open(output_file_path, "w") as output_file:
        output_file.writelines(gcode_content)

    print(f"Commented Gcode written to '{output_file_path}'.")

def get_gcode_commands_from_lines(input_file_path, line_numbers):
    gcode_commands = []

    with open(input_file_path, "r") as input_file:
        lines = input_file.readlines()

    for line_number in line_numbers:
        if 1 <= line_number <= len(lines):
            line = lines[line_number - 1].strip()  # Adjust index to 0-based
            if line.startswith(";"):
                # Skip comments or other non-G-code lines
                continue
            gcode_commands.append(line)

    return gcode_commands

def get_t_commands(input_file_path):
    # Find the line numbers for the filament swaps "M620 SiA", "M621 SiA", and "T0-T7"
    m620_swaps, m621_swaps, t_swaps = swap_finder(input_file_path)
    # Fix the filament numbers and get the corrected swaps list
    corrected_swaps_list = swap_finder_fixer(input_file_path, m620_swaps)
    #print(corrected_swaps_list)
    start_line = gcode_start_locator(input_file_path)
    end_line = first_layer_end(input_file_path)
    
    start_line_numbers = []
    middle_line_numbers = []
    end_line_numbers = []

    for swap_count, swap_data in enumerate(corrected_swaps_list, start=1):
        filament_number = swap_data["filament_number"]
        start_lines = filter_output(swap_data["start_lines"], start_line, end_line)
        middle_lines = filter_output(swap_data["middle_lines"], start_line, end_line)
        end_lines = filter_output(swap_data["end_lines"], start_line, end_line)

        if not start_lines and not middle_lines and not end_lines:
            continue  # Skip swaps that are outside the filtered range

        start_line_numbers.extend(start_lines)
        middle_line_numbers.extend(middle_lines)
        end_line_numbers.extend(end_lines)
    
    t_commands = get_gcode_commands_from_lines(input_file_path, middle_line_numbers)
    
    return (t_commands)

if __name__ == "__main__":
    import sys
    sys.path.append(".")

    # File paths
    if len(sys.argv) > 1:
        input_file_path = sys.argv[1]
    else:
        input_file_path = "example.gcode"

    t_commands = get_t_commands(input_file_path)

    # Run the GUI or command-line operations based on the number of arguments
    if len(sys.argv) == 1:
        import gui
    elif len(sys.argv) == 3:
        t_command1, t_command2 = sys.argv[1], sys.argv[2]
        copy_features(input_file_path, t_command1, t_command2)
        generate_instructions(input_file_path, t_command1, t_command2)
    elif len(sys.argv) == 2 and sys.argv[1] == "calibration_off":
        modify_gcode_cal(input_file_path)
    else:
        print("Invalid arguments. Usage: main.py [input_file_path] | [t_command1] [t_command2] | calibration_off")
