# Test Content Validation
This Python script can be used to validate CTA WAVE Test Content vectors 
[here](https://dash.akamaized.net/WAVE/vectors/).

Requirements:
- [Python 3](https://www.python.org)
- [ffmpeg and ffprobe](http://ffmpeg.org/)
- [MP4Box](http://gpac.io/)
- [lxml](https://lxml.de/)

To use:
1. Download the CTA WAVE test vectors to a local folder.
2. Download a CSV copy of the corresponding test content definition matrix such as 
[this](https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/) for AVC.
3. Download `tcval.py` and  `requirements.txt`.
4. Run `pip install -r requirements.txt` to install dependencies (lxml).
5. Run `tcval.py -m <path_to_CSV> -v <path to vectors folder>`.

Example:
`tcval.py -m "WAVE test content _ test code sparse Matrix - AVC - Sheet1.csv" -v CTA\vectors\`

Note: when the `-m` parameter is not provided, the script downloads the 
[latest CSV matrix for AVC](https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/).