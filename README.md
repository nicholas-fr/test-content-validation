# Test Content Validation
This Python script can be used to validate CTA WAVE Test Content vectors [here](https://dash.akamaized.net/WAVE/vectors/).

Requirements:
- [Python](https://www.python.org)
- [ffmpeg and ffprobe](http://ffmpeg.org/)
- [mp4box](http://gpac.io/)

To use:
1. Download the test vectors to a local folder.
2. Download a CSV copy of the corresponding test content definition matrix such as [this](https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/) for AVC
3. Download tcval.py
4. Run `tcval.py -m <path_to_CSV> -v <path to vectors folder>`

Example:
`tcval.py -m "WAVE test content _ test code sparse Matrix - AVC - Sheet1.csv" -v CTA\vectors\`
