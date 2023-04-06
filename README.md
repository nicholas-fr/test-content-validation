# Test Content Validation
This Python script can be used to validate CTA WAVE Test Content vectors 
[here](https://dash.akamaized.net/WAVE/vectors/).

Requirements:
- [Python 3](https://www.python.org) (recommend >=3.10)
- Python modules:
  - [lxml](https://lxml.de/)
  - [isodate](https://github.com/gweis/isodate/)
- [ffmpeg & ffprobe](http://ffmpeg.org/)
- [MP4Box](http://gpac.io/)

To use:
1. Download the CTA WAVE test vectors to a local folder.
2. Download a CSV copy of the corresponding test content definition matrix such as 
[this](https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/) for AVC.
3. Download `tcval.py` and  `requirements.txt`.
4. Run `pip install -r requirements.txt` to install dependencies.
5. Run `tcval.py -m <path to CSV> -v <path to vectors folder> --mezzanineversion <expected mezzanine version used to generate the test vectors> -d <Docker container ID running JCCP DASH validator> --ip <IP address of local machine to be used by Docker instance>`.

Example:
`tcval.py -m matrix_avc.csv -v CTA\vectors\development --mezzanineversion 4 -d e36693a4b861 --ip 192.168.2.110`

Notes: 
- When the `-m` parameter is not provided, the script downloads the 
[latest CSV matrix for AVC](https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/).
- When the `-d` parameter is present and the referenced Docker container is present, 
each test vector will also be validated using the JCCP DASH validator.
For more information please refer to: https://github.com/Dash-Industry-Forum/DASH-IF-Conformance
- When the `--ip` parameter is not provided the IP address the Docker instance will connect to in order to access 
the test vectors will be autodetected, but it may not be the correct address if the local machine has mulitple 
network interfaces.