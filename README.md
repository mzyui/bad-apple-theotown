# Bad Apple but it's Theotown

### Prerequisites

Before running the script, you need to have the following command-line tools installed and available in your system's PATH:

-   `ffmpeg`: For extracting frames and audio from the video.
-   `jp2a`: For converting image frames to ASCII art.

### Usage

The main script is `generate.py`. You can customize its behavior using command-line arguments.

To see all available options, run:

```bash
python generate.py --help
```

#### Basic Execution

To run the script with default settings, simply execute:

```bash
python generate.py
```

This will use the `bad_apple.mp4` file in the current directory and generate the output.

### Installation and Usage (TheoTown on Android)

These instructions are for using the generated Lua script in TheoTown on Android.

**Prerequisites:**

-   Your Android device must be **rooted**.
-   You have TheoTown installed.

**Steps:**

1.  **Generate the Script**: Run `python generate.py` on your computer. This will create directory containing the `render.lua` file.

2.  **Transfer to Device**: Move the entire `output-dir` folder from your computer to your Android device.

3.  **Place in Plugins Folder**: Using a root-enabled file manager on your Android device, move the `output-raw` folder into the following directory:
    `Android/data/info.flowersoft.theotown.theotown/files/plugins/`

4.  **Trigger in Game**:
    -   Open TheoTown.
    -   Create a new **Region** (or world) and use the seed `flat`.
    -   Within that region, create a new **City** and name it exactly `Bad Apple`. The name is case-sensitive.

    Entering the city will automatically trigger the animation.


## Output

The script will produce the following files:

-   `render.lua`: The final Lua script containing the animation data.
-   `frames-ascii/`: A directory containing the individual ASCII art frames.
-   `frames-jpg/`: A directory of temporary frames extracted from the video.
