# AMS_filament_swapper
Application to help you re-order how filaments are swapped on the Bambu X1C printer with AMS. Only works on the first layer, excluding last filament swap, only works with up to 8 filaments.

I made this for myself and my specific setup, please use this at your own risk. This may damage your printer.

I would call this code pre-alpha. It's still doesn't have all the features I want it to have eventually. 

Note this only works with gcode generated by Bambu Studio 1.7.2.51.

Instructions.
1. Run gui.py from the command console.
2. Browse for your input gcode file.
3. Click "Analyse" button.
4. Select two, and only two filaments to swap, excluding the first and last ones shown.
5. Click "Generate Swaps"
6. Optional - click "Turn Calibration Off"
7. Optional - click "Debug"

Current features implemented:
1 Selection of input gcode file
2. Identify filament swaps in gcode file up to 8 filaments.
3. Generate files with sections of code for user to manually overwrite, based on selection.
4. Generate output file with calibration commented out, if user doesn't want to do run flow calibration.
5. Generate gcode instructions file.
6. Generate debug file with line locations of commands and comments being used as keys in the gcode file.

Features wishlist:
1. Support up to 16 filaments.
2. Support filament swaps on more than just 1st layer.
3. Suppart swapping last filament on 1st layer.
4. Automatically generate usable output gcode instead of just instructions and pasted code for the user to manually change.
5. Handle errors.
