#!/usr/bin/env python3
import concurrent.futures
import subprocess
import shutil
import glob
import os
import sys
import argparse


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def convert_frame(jpg_path, out_frames_dir, width, height):
    name = os.path.splitext(os.path.basename(jpg_path))[0]
    out_txt = f"{out_frames_dir}/{name}.txt"
    run(
        [
            "jp2a",
            jpg_path,
            f"--width={width}",
            f"--height={height}",
            "--chars=01",
            f"--output={out_txt}",
        ]
    )
    return out_txt


def main():
    parser = argparse.ArgumentParser(description="Bad Apple but it's Theotown")
    parser.add_argument(
        "--video", default="bad_apple.mp4", help="Path to the input video file."
    )
    parser.add_argument(
        "--fps", type=int, default=30, help="Frames per second for extraction."
    )
    parser.add_argument(
        "--width", type=int, default=64, help="Width of the ASCII output."
    )
    parser.add_argument(
        "--height", type=int, default=64, help="Height of the ASCII output."
    )
    parser.add_argument(
        "--start-x",
        type=int,
        default=0,
        help="X offset for the render in the Lua script.",
    )
    parser.add_argument(
        "--start-y",
        type=int,
        default=0,
        help="Y offset for the render in the Lua script.",
    )
    parser.add_argument(
        "--tmp-frames-dir",
        default="frames-jpg",
        help="Directory for temporary JPG frames.",
    )
    parser.add_argument(
        "--out-frames-dir",
        default="frames-ascii",
        help="Directory for output ASCII frames.",
    )
    parser.add_argument(
        "--out-lua-dir",
        default="bad_apple",
        help="Directory for the output Lua script. The filename will always be 'render.lua'.",
    )
    args = parser.parse_args()

    print("--- Settings ---")
    print(f"Video file: {args.video}")
    print(f"FPS: {args.fps}")
    print(f"Output Resolution: {args.width}x{args.height}")
    print(f"Render Start Offset (X,Y): ({args.start_x}, {args.start_y})")
    print(f"Temporary JPG Frames Directory: {args.tmp_frames_dir}")
    print(f"Output ASCII Frames Directory: {args.out_frames_dir}")
    print(f"Output Lua Directory: {args.out_lua_dir}")
    print("----------------")
    print()  # Add an empty line for better readability

    for d in (args.tmp_frames_dir, args.out_frames_dir, args.out_lua_dir):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)

    output_lua_path = os.path.join(args.out_lua_dir, "render.lua")

    if os.path.exists(output_lua_path):
        os.remove(output_lua_path)

    print("[1/4] Extracting frames")
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            args.video,
            "-vf",
            f"fps={args.fps}",
            f"{args.tmp_frames_dir}/out%04d.jpg",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )



    print("[2/4] Converting frames to ASCII")
    jpgs = sorted(glob.glob(f"{args.tmp_frames_dir}/*.jpg"))
    if not jpgs:
        print("No frames generated", file=sys.stderr)
        sys.exit(1)

    total_jpgs = len(jpgs)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                convert_frame, jpg, args.out_frames_dir, args.width, args.height
            ): jpg
            for jpg in jpgs
        }
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            jpg_path = futures[future]
            try:
                out_txt = future.result()
                progress = (
                    f"  ({i + 1}/{total_jpgs}) Converted {os.path.basename(out_txt)}"
                )
                print(progress.ljust(80), end="\r")
            except Exception as exc:
                print(f"\nError converting {jpg_path}: {exc}", file=sys.stderr)
    print()

    print("[3/4] Generating render.lua")

    txts = sorted(glob.glob(f"{args.out_frames_dir}/out*.txt"))

    all_pixel_lines = []
    for txt in txts:
        with open(txt, "r") as f:
            lines = f.read().splitlines()
        if len(lines) != args.height:
            raise ValueError(f"{txt}: height mismatch")
        all_pixel_lines.append(list(reversed(lines)))

    lua_frames = []
    previous_lines = None

    hex_frame_char_count = args.height * ((args.width + 7) // 8 * 2)
    delta_threshold_items = hex_frame_char_count / 10

    for i, current_lines in enumerate(all_pixel_lines):
        is_keyframe = False
        if i == 0:
            is_keyframe = True
        else:
            delta = []
            for y in range(args.height):
                for x in range(args.width):
                    if current_lines[y][x] != previous_lines[y][x]:
                        val = current_lines[y][x]
                        delta.append("{%d,%d,%s}" % (x + 1, y + 1, val))

            if len(delta) > delta_threshold_items:
                is_keyframe = True

        if is_keyframe:
            frame_hex_lines = []
            for line in current_lines:
                if len(line) != args.width:
                    raise ValueError(f"Width mismatch in frame {i} for line '{line}'")

                byte_values = bytearray()
                for k in range(0, len(line), 8):
                    chunk = line[k : k + 8].ljust(8, "0")
                    byte_values.append(int(chunk, 2))

                hex_string = byte_values.hex()
                frame_hex_lines.append(f'            "{hex_string}"')

            full_frame_data = ",\n".join(frame_hex_lines)
            lua_frames.append(
                "    {type='full', data={\n%s\n        }}" % full_frame_data
            )
        else:
            delta_data = ",\n".join(delta)
            if delta_data:
                lua_frames.append("    {type='delta', data={%s}}" % delta_data)
            else:
                lua_frames.append("    {type='delta', data={}}")

        previous_lines = current_lines

    frames = ",\n".join(lua_frames)

    with open(output_lua_path, "w") as lua:
        lua.write(
            f"""-- THIS FILE IS AUTO-GENERATED. DO NOT EDIT.
    -- Copyright (c) 2026 mzyui (github.com/mzyui). All rights reserved.

    local ALIVE_CELL = "$asphalt04"
    local DEAD_CELL  = "$asphalt01"
    
    local START_X = {args.start_x}
    local START_Y = {args.start_y}
    
    local WIDTH  = {args.width}
    local HEIGHT = {args.height}
    local FPS = {args.fps}
    
    local frameIndex = 1
    local counter = 0
    local startTime = 0
    local isRunning = false
    
    local MAP_FRAMES = {{
    {frames}
    }}
    
    local TOTAL_FRAMES = #MAP_FRAMES
    local currentFrameState = {{}}
    
    local rowCache = {{}}
    
    local function hexToBits(hex_str)
        if rowCache[hex_str] then
            return rowCache[hex_str]
        end
    
        local bits = ""
        for i = 1, #hex_str, 2 do
            local byte = tonumber(string.sub(hex_str, i, i + 1), 16)
            for j = 7, 0, -1 do
                if bit32.band(byte, 2^j) > 0 then
                    bits = bits .. "1"
                else
                    bits = bits .. "0"
                end
            end
        end
    
        local result = string.sub(bits, 1, WIDTH) 
        rowCache[hex_str] = result
        return result
    end
    
    local function drawFullFrame()
        for y = 1, HEIGHT do
            for x = 1, WIDTH do
                local pixel = currentFrameState[y][x]
                local wx = START_X + x - 1
                local wy = START_Y + y - 1
                Builder.buildGround(pixel == '1' and ALIVE_CELL or DEAD_CELL, wx, wy)
            end
        end
    end
    
    local function applyDelta(delta_data)
        for _, change in ipairs(delta_data) do
            local x, y, val_num = change[1], change[2], change[3]
            local val_str = tostring(val_num)
            currentFrameState[y][x] = val_str
            local wx = START_X + x - 1
                local wy = START_Y + y - 1
                Builder.buildGround(val_str == '1' and ALIVE_CELL or DEAD_CELL, wx, wy)
            end
        end
    
        local function decodeFullFrame(frame_data)
            for y = 1, HEIGHT do
                local bits_row = hexToBits(frame_data[y])
                if not currentFrameState[y] then currentFrameState[y] = {{}} end
                for x = 1, WIDTH do
                    currentFrameState[y][x] = string.sub(bits_row, x, x)
                end
            end
        end
    
        function script:enterCity()
            startTime = os.clock()
            isRunning = City.getName() == "Bad Apple" and City.getSeed() == "flat"
    
            if isRunning then
                frameIndex = 1
                local first_frame = MAP_FRAMES[1]
    
                decodeFullFrame(first_frame.data)
                drawFullFrame()
    
                Debug.toast("Bad Apple @fb.com/mzyui @github.com/mzyui")
            end
        end
    
        function script:update()
            if not isRunning then return end
    
            local elapsed = os.clock() - startTime
            local expectedFrameIndex = math.floor(elapsed * FPS) + 1
    
            if expectedFrameIndex > TOTAL_FRAMES then
                isRunning = false
                return
            end
    
            while frameIndex < expectedFrameIndex do
                frameIndex = frameIndex + 1
                local frame = MAP_FRAMES[frameIndex]
                if frame then
                    if frame.type == 'full' then
                        decodeFullFrame(frame.data)
                        drawFullFrame()
                    elseif frame.type == 'delta' then
                        applyDelta(frame.data)
                    end
                end
            end
        end
        """.lstrip()
        )

    entry_point_content = """[{
      "id":"$badapple",
      "type":"script",
      "script":"render.lua"
    }]"""
    entry_point_path = os.path.join(args.out_lua_dir, "entry_point.json")
    with open(entry_point_path, "w") as f:
        f.write(entry_point_content)

    print("[4/4] Done")

    file_size_bytes = os.path.getsize(output_lua_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    print(
        f"✔ Generated {output_lua_path} with {len(txts)} frames (Size: {file_size_mb:.2f} MB)"
    )


if __name__ == "__main__":
    main()
