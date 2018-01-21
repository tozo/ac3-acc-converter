#!/usr/bin/python

import sys
import os
import subprocess
import json
import getopt
from io import StringIO

# We will work only with files that have the extension defined in this array
allowed_suffixes = ["mkv", "avi"]

# The codec names listed in the "excluded_codec_names" will not be mapped to the output.
# They have to be excluded, otherwise the conversion will not work.
excluded_codec_names = ["png", "mjpeg"]

# If the video codes name is something different than what is defined in this list, convert it to h264
allowed_video_codec_names = ["h264"]

convert_video_stream = False


def is_extension_allowed(file_name):
    # Determines whether the file name ends with the correct suffix or not.
    for suffix in allowed_suffixes:
        if str.endswith(file_name, suffix):
            return True


def is_codec_name_allowed(codec_name):
    # Determines whether the code name is allowed or not
    for exc_codec_name in excluded_codec_names:
        if exc_codec_name == codec_name:
            return False
    return True


def is_video_codec_correct_format(codec_name):
    # Determines whether the video code name is allowed or not
    for allowed_video_codec_name in allowed_video_codec_names:
        if allowed_video_codec_name == codec_name:
            return True
    return False


def convertible_streams(absolute_path):
    # Returns with an array of stream indexes that can be converted by ffmpeg.
    stream_info_command = "ffprobe.exe -loglevel quiet -print_format json  -show_entries stream=index,codec_name " + absolute_path
    details = subprocess.check_output(stream_info_command)
    info = json.load(StringIO(details.decode("utf-8")))
    result = []
    for stream in info['streams']:
        if is_codec_name_allowed(stream['codec_name']):
            result.append("0:" + str(stream['index']))
        
        if stream['index'] == 0:
            if not is_video_codec_correct_format(stream['codec_name']):
                global convert_video_stream
                convert_video_stream = True

    return result


def convert_stream_indexes_to_map(stream_array):
    # Returns with a string that includes all the mappings required for ffmpeg
    result = ""
    for stream in stream_array:
        result += " -map " + stream
    return result


def normalize_url(url):
    # Normalize the urls passed as an argument by removing the '\\' at the end of it.
    if str.endswith(url, os.path.sep):
        url = url[:-1]
    return url


def iterate_files(files, root, append_to_output_file_name, output_folder):
    # This method iterates over the input files and runs the conversion if it necessary.

    number_of_files = 0

    for file_name in files:
        split_file_name = os.path.splitext(file_name)

        absolute_input_path = root + os.path.sep + file_name
        absolute_output_path = output_folder + os.path.sep + split_file_name[0] + append_to_output_file_name + split_file_name[1]

        if os.path.isfile(absolute_input_path) and is_extension_allowed(file_name):
            mappings = convert_stream_indexes_to_map(convertible_streams(absolute_input_path))
            
            video_stream_operation = "copy"
            if convert_video_stream:
                video_stream_operation = "libx264"

            # If there are lot of "Past duration X.XXXX too large" errors, add '-vf "fps=30"' to the command
            command = "ffmpeg.exe -i " + absolute_input_path + mappings + " -c:v " + video_stream_operation + " -c:a aac -strict experimental -c:s copy " + absolute_output_path
            print("Running the code: \"" + command + "\"")
            os.system(command)
            number_of_files += 1
    return number_of_files


def main(argv):

    input_folder = ''
    output_folder = ''
    append_to_output_file_name = ''
    depth = 0
    number_of_files_converted = 0

    try:
        opts, args = getopt.getopt(argv, "i:o:a:d:", ["input-folder=", "output-folder=", "append-to-name=", "depth="])
    except getopt.GetoptError as error:
        print(str(error))
        sys.exit()

    for opt, arg in opts:
        if opt in ('-i', '--input-folder'):
            input_folder = normalize_url(arg)
        elif opt in ('-o', '--output-folder'):
            output_folder = normalize_url(arg)
        elif opt in ('-a', '--append-to-name'):
            append_to_output_file_name = arg
        elif opt in ('-d', '--depth'):
            depth = int(arg)

    for root, dirs, files in os.walk(input_folder, topdown=True):
        folder_depth = root.count(os.path.sep) - input_folder.count(os.path.sep)

        if folder_depth <= depth:
            number_of_files_converted += iterate_files(files, root, append_to_output_file_name, output_folder)

    print("The number of files converted: " + str(number_of_files_converted))


if __name__ == '__main__':
    main(sys.argv[1:])
