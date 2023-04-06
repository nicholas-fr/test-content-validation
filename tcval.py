#!/usr/bin/env python3

import argparse
import copy
import csv
import errno
import isodate
import json
import os
import shutil
import socket
import string
import subprocess
import sys
import time
import urllib.request
import zipfile

from collections import Counter
from datetime import datetime
from decimal import *
from enum import Enum
from json import JSONEncoder
from lxml import etree
from pathlib import Path


class CmafInitConstraints(str, Enum):
	SINGLE: str = 'single'
	MULTIPLE: str = 'multiple'


class CmafChunksPerFragment(str, Enum):
	SINGLE: str = 'one chunk per fragment'
	MULTIPLE: str = 'multiple chunks per fragment, multiple samples per chunk'
	MULTIPLE_CHUNKS_ARE_SAMPLES: str = 'multiple chunks per fragment, each chunk is one sample'


class TestResult(str, Enum):
	PASS: str = 'pass'
	FAIL: str = 'fail'
	NOT_TESTABLE: str = 'not testable'
	NOT_TESTED: str = 'not tested'
	NOT_APPLICABLE: str = 'not applicable'
	UNKNOWN: str = 'unknown'


class VideoResolution:
	horizontal = 0
	vertical = 0
	
	def __init__(self, horizontal=None, vertical=None):
		if horizontal is not None:
			self.horizontal = horizontal
		if vertical is not None:
			self.vertical = vertical
			
	def json(self):
		return {
			'horizontal': self.horizontal,
			'vertical': self.vertical
		}
	# Use same JSON export for all TestContent json export functions
	json_def = json_analysis = json_ref = json_full = json


# Arrays representing:
#   - expected value (read from input test content matrix), 
#   - value determined from stream analysis,
#   - test status (pass/fail)

class TestContent:
	test_stream_id = ''
	test_file_path = ''
	mezzanine_version = ['', '', TestResult.NOT_TESTED]
	mezzanine_format = ['', '', TestResult.NOT_TESTED]
	conformance_test_result = ''
	codec_name = ['', '', TestResult.NOT_TESTED]
	codec_profile = ['', '', TestResult.NOT_TESTED]
	codec_level = ['', '', TestResult.NOT_TESTED]
	codec_tier = ['', '', TestResult.NOT_TESTED]
	file_brand = ['', '', TestResult.NOT_TESTED]
	sample_entry_type = ['', '', TestResult.NOT_TESTED]
	parameter_sets_in_cmaf_header_present = ['', '', TestResult.NOT_TESTED]
	parameter_sets_in_band_present = ['', '', TestResult.NOT_TESTED]
	picture_timing_sei_present = ['', '', TestResult.NOT_TESTED]
	vui_timing_present = ['', '', TestResult.NOT_TESTED]
	cmaf_fragment_duration = [0, 0, TestResult.NOT_TESTED]
	cmaf_initialisation_constraints = ['', '', TestResult.NOT_TESTABLE]  # Not testable with current test content
	chunks_per_fragment = [0, 0, TestResult.NOT_TESTED]
	b_frames_present = ['', '', TestResult.NOT_TESTED]
	resolution = [VideoResolution(), VideoResolution(), TestResult.NOT_TESTED]
	frame_rate = [0.0, 0.0, TestResult.NOT_TESTED]
	bitrate = [0, 0, TestResult.NOT_TESTED]
	duration = [0, 0, TestResult.NOT_TESTED]
	mpd_sample_duration_delta = [0.0, 0.0, TestResult.NOT_TESTED]
	
	
	def __init__(self, test_stream_id=None, test_file_path=None, mezzanine_version=None, mezzanine_format=None,
				conformance_test_result=None, codec_name=None, codec_profile=None, codec_level=None, codec_tier=None,
				file_brand=None, sample_entry_type=None, parameter_sets_in_cmaf_header_present=None,
				parameter_sets_in_band_present=None, picture_timing_sei_present=None, vui_timing_present=None,
				cmaf_fragment_duration=None, cmaf_initialisation_constraints=None, chunks_per_fragment=None,
				b_frames_present=None, resolution=None, frame_rate=None, bitrate=None, duration=None,
				mpd_sample_duration_delta=None):
		if test_stream_id is not None:
			self.test_stream_id = test_stream_id
		if test_file_path is not None:
			self.test_file_path = test_file_path
		if mezzanine_version is not None:
			self.mezzanine_version = [mezzanine_version, '', TestResult.NOT_TESTED]
		if mezzanine_format is not None:
			self.mezzanine_format = [mezzanine_format, '', TestResult.NOT_TESTED]
		if conformance_test_result is not None:
			self.conformance_test_result = conformance_test_result
		if codec_name is not None:
			self.codec_name = [codec_name, '', TestResult.NOT_TESTED]
		if codec_profile is not None:
			self.codec_profile = [codec_profile, '', TestResult.NOT_TESTED]
		if codec_level is not None:
			self.codec_level = [codec_level, '', TestResult.NOT_TESTED]
		if codec_tier is not None:
			self.codec_tier = [codec_tier, '', TestResult.NOT_TESTED]
		if file_brand is not None:
			self.file_brand = [file_brand, '', TestResult.NOT_TESTED]
		if sample_entry_type is not None:
			self.sample_entry_type = [sample_entry_type, '', TestResult.NOT_TESTED]
		if parameter_sets_in_cmaf_header_present is not None:
			self.parameter_sets_in_cmaf_header_present = [parameter_sets_in_cmaf_header_present, '', TestResult.NOT_TESTED]
		if parameter_sets_in_band_present is not None:
			self.parameter_sets_in_band_present = [parameter_sets_in_band_present, '', TestResult.NOT_TESTED]
		if picture_timing_sei_present is not None:
			self.picture_timing_sei_present = [picture_timing_sei_present, '', TestResult.NOT_TESTED]
		if vui_timing_present is not None:
			self.vui_timing_present = [vui_timing_present, '', TestResult.NOT_TESTED]
		if cmaf_fragment_duration is not None:
			self.cmaf_fragment_duration = [cmaf_fragment_duration, 0, TestResult.NOT_TESTED]
		if cmaf_initialisation_constraints is not None:
			self.cmaf_initialisation_constraints = [cmaf_initialisation_constraints, '', TestResult.NOT_TESTABLE]
		if chunks_per_fragment is not None:
			self.chunks_per_fragment = [chunks_per_fragment, 0, TestResult.NOT_TESTED]
		if b_frames_present is not None:
			self.b_frames_present = [b_frames_present, '', TestResult.NOT_TESTED]
		if resolution is not None:
			self.resolution = [resolution, VideoResolution(), TestResult.NOT_TESTED]
		if frame_rate is not None:
			self.frame_rate = [frame_rate, 0.0, TestResult.NOT_TESTED]
		if bitrate is not None:
			self.bitrate = [bitrate, 0, TestResult.NOT_TESTED]
		if duration is not None:
			self.duration = [duration, 0, TestResult.NOT_TESTED]
		if mpd_sample_duration_delta is not None:
			self.mpd_sample_duration_delta = [mpd_sample_duration_delta, 0.0, TestResult.NOT_TESTED]
	
	def json_def(self):
		return {
			'test_stream_id': self.test_stream_id,
			'test_file_path': self.test_file_path,
			'mezzanine_version': self.mezzanine_version[0],
			'mezzanine_format': self.mezzanine_format[0],
			'conformance_test_result': '',  # Only applicable for results
			'codec_profile': self.codec_profile[0],
			'codec_level': self.codec_level[0],
			'codec_tier': self.codec_tier[0],
			'file_brand': self.file_brand[0],
			'sample_entry_type': self.sample_entry_type[0],
			'parameter_sets_in_cmaf_header_present': self.parameter_sets_in_cmaf_header_present[0],
			'parameter_sets_in_band_present': self.parameter_sets_in_band_present[0],
			'picture_timing_sei_present': self.picture_timing_sei_present[0],
			'vui_timing_present': self.vui_timing_present[0],
			'cmaf_fragment_duration': self.cmaf_fragment_duration[0],
			'cmaf_initialisation_constraints': self.cmaf_initialisation_constraints[0],
			'chunks_per_fragment': self.chunks_per_fragment[0],
			'b_frames_present': self.b_frames_present[0],
			'resolution': self.resolution[0],
			'frame_rate': self.frame_rate[0],
			'bitrate': self.bitrate[0],
			'duration': self.duration[0],
			'mpd_sample_duration_delta': self.mpd_sample_duration_delta[0]
		}
	
	def json_analysis(self):
		return {
			'test_stream_id': self.test_stream_id,
			'test_file_path': self.test_file_path,
			'mezzanine_version': self.mezzanine_version[1],
			'mezzanine_format': self.mezzanine_format[1],
			'conformance_test_result': '',  # Only applicable for results
			'codec_profile': self.codec_profile[1],
			'codec_level': self.codec_level[1],
			'codec_tier': self.codec_tier[1],
			'file_brand': self.file_brand[1],
			'sample_entry_type': self.sample_entry_type[1],
			'parameter_sets_in_cmaf_header_present': self.parameter_sets_in_cmaf_header_present[1],
			'parameter_sets_in_band_present': self.parameter_sets_in_band_present[1],
			'picture_timing_sei_present': self.picture_timing_sei_present[1],
			'vui_timing_present': self.vui_timing_present[1],
			'cmaf_fragment_duration': self.cmaf_fragment_duration[1],
			'cmaf_initialisation_constraints': self.cmaf_initialisation_constraints[1],
			'chunks_per_fragment': self.chunks_per_fragment[1],
			'b_frames_present': self.b_frames_present[1],
			'resolution': self.resolution[1],
			'frame_rate': self.frame_rate[1],
			'bitrate': self.bitrate[1],
			'duration': self.duration[1],
			'mpd_sample_duration_delta': self.mpd_sample_duration_delta[1]
		}
	
	def json_res(self):
		return {
			'test_stream_id': self.test_stream_id,
			'test_file_path': self.test_file_path,
			'mezzanine_version': self.mezzanine_version[2],
			'mezzanine_format': self.mezzanine_format[2],
			'conformance_test_result': self.conformance_test_result,
			'codec_profile': self.codec_profile[2],
			'codec_level': self.codec_level[2],
			'codec_tier': self.codec_tier[2],
			'file_brand': self.file_brand[2],
			'sample_entry_type': self.sample_entry_type[2],
			'parameter_sets_in_cmaf_header_present': self.parameter_sets_in_cmaf_header_present[2],
			'parameter_sets_in_band_present': self.parameter_sets_in_band_present[2],
			'picture_timing_sei_present': self.picture_timing_sei_present[2],
			'vui_timing_present': self.vui_timing_present[2],
			'cmaf_fragment_duration': self.cmaf_fragment_duration[2],
			'cmaf_initialisation_constraints': self.cmaf_initialisation_constraints[2],
			'chunks_per_fragment': self.chunks_per_fragment[2],
			'b_frames_present': self.b_frames_present[2],
			'resolution': self.resolution[2],
			'frame_rate': self.frame_rate[2],
			'bitrate': self.bitrate[2],
			'duration': self.duration[2],
			'mpd_sample_duration_delta': self.mpd_sample_duration_delta[2]
		}
		
	def json_full(self):
		return {
			'TestStreamValidation': {
				'test_stream_id': self.test_stream_id,
				'test_file_path': self.test_file_path,
				'mezzanine_version': {
					'expected': self.mezzanine_version[0],
					'detected': self.mezzanine_version[1],
					'test_result': self.mezzanine_version[2].value
					},
				'mezzanine_format': {
					'expected': self.mezzanine_format[0],
					'detected': self.mezzanine_format[1],
					'test_result': self.mezzanine_format[2].value
					},
				'conformance_test_result': self.conformance_test_result,
				'codec_profile': {
					'expected': self.codec_profile[0],
					'detected': self.codec_profile[1],
					'test_result': self.codec_profile[2].value
					},
				'codec_level': {
					'expected': self.codec_level[0],
					'detected': self.codec_level[1],
					'test_result': self.codec_level[2].value
					},
				'codec_tier': {
					'expected': self.codec_tier[0],
					'detected': self.codec_tier[1],
					'test_result': self.codec_tier[2].value
					},
				'file_brand': {
					'expected': self.file_brand[0],
					'detected': self.file_brand[1],
					'test_result': self.file_brand[2].value
					},
				'sample_entry_type': {
					'expected': self.sample_entry_type[0],
					'detected': self.sample_entry_type[1],
					'test_result': self.sample_entry_type[2].value
					},
				'parameter_sets_in_cmaf_header_present': {
					'expected': self.parameter_sets_in_cmaf_header_present[0],
					'detected': self.parameter_sets_in_cmaf_header_present[1],
					'test_result': self.parameter_sets_in_cmaf_header_present[2].value
					},
				'parameter_sets_in_band_present': {
					'expected': self.parameter_sets_in_band_present[0],
					'detected': self.parameter_sets_in_band_present[1],
					'test_result': self.parameter_sets_in_band_present[2].value
					},
				'picture_timing_sei_present': {
					'expected': self.picture_timing_sei_present[0],
					'detected': self.picture_timing_sei_present[1],
					'test_result': self.picture_timing_sei_present[2].value
					},
				'vui_timing_present': {
					'expected': self.vui_timing_present[0],
					'detected': self.vui_timing_present[1],
					'test_result': self.vui_timing_present[2].value
					},
				'cmaf_fragment_duration': {
					'expected': self.cmaf_fragment_duration[0],
					'detected': self.cmaf_fragment_duration[1],
					'test_result': self.cmaf_fragment_duration[2].value
					},
				'cmaf_initialisation_constraints': {
					'expected': self.cmaf_initialisation_constraints[0],
					'detected': self.cmaf_initialisation_constraints[1],
					'test_result': self.cmaf_initialisation_constraints[2].value
					},
				'chunks_per_fragment': {
					'expected': self.chunks_per_fragment[0],
					'detected': self.chunks_per_fragment[1],
					'test_result': self.chunks_per_fragment[2].value
					},
				'b_frames_present': {
					'expected': self.b_frames_present[0],
					'detected': self.b_frames_present[1],
					'test_result': self.b_frames_present[2].value
					},
				'resolution': {
					'expected': self.resolution[0],
					'detected': self.resolution[1],
					'test_result': self.resolution[2].value
					},
				'frame_rate': {
					'expected': self.frame_rate[0],
					'detected': self.frame_rate[1],
					'test_result': self.frame_rate[2].value
					},
				'bitrate': {
					'expected': self.bitrate[0],
					'detected': self.bitrate[1],
					'test_result': self.bitrate[2].value
					},
				'duration': {
					'expected': self.duration[0],
					'detected': self.duration[1],
					'test_result': self.duration[2].value
					},
				'mpd_sample_duration_delta': {
					'expected': self.mpd_sample_duration_delta[0],
					'detected': self.mpd_sample_duration_delta[1],
					'test_result': self.mpd_sample_duration_delta[2].value
					}
			}
		}


class TestContentDefEncoder(JSONEncoder):
	def default(self, o):
		if "json_def" in dir(o):
			return o.json_def()
		return JSONEncoder.default(self, o)

		
class TestContentAnalysisEncoder(JSONEncoder):
	def default(self, o):
		if "json_analysis" in dir(o):
			return o.json_analysis()
		return JSONEncoder.default(self, o)


class TestContentResEncoder(JSONEncoder):
	def default(self, o):
		if "json_res" in dir(o):
			return o.json_res()
		return JSONEncoder.default(self, o)


class TestContentFullEncoder(JSONEncoder):
	def default(self, o):
		if "json_full" in dir(o):
			return o.json_full()
		return JSONEncoder.default(self, o)


class SwitchingSetTestContent:
	switching_set_id = ''
	test_stream_ids = [[''], [''], [TestResult.NOT_TESTED]]
	test_file_paths = [[''], [''], [TestResult.NOT_TESTED]]
	mezzanine_version = ['', '', TestResult.NOT_TESTED]
	conformance_test_result = ''
	cmaf_initialisation_constraints = ['', '', TestResult.NOT_TESTED]

	def __init__(self, switching_set_id=None, test_stream_ids=None, test_file_paths=None, mezzanine_version=None,
				conformance_test_result=None, cmaf_initialisation_constraints=None):
		if switching_set_id is not None:
			self.switching_set_id = switching_set_id
		if test_stream_ids is not None:
			self.test_stream_ids = [test_stream_ids, [''] * len(test_stream_ids), [TestResult.NOT_TESTED] * len(test_stream_ids)]
		if test_file_paths is not None:
			self.test_file_paths = [test_file_paths, [''] * len(test_file_paths), [TestResult.NOT_TESTED] * len(test_file_paths)]
		if mezzanine_version is not None:
			self.mezzanine_version = [mezzanine_version, '', TestResult.NOT_TESTED]
		if conformance_test_result is not None:
			self.conformance_test_result = conformance_test_result
		if cmaf_initialisation_constraints is not None:
			self.cmaf_initialisation_constraints = [cmaf_initialisation_constraints, '', TestResult.NOT_TESTED]
	
	def json_def(self):
		return {
			'switching_set_id': self.switching_set_id,
			'test_stream_ids': self.test_stream_ids[0],
			'test_file_paths': self.test_file_paths[0],
			'mezzanine_version': self.mezzanine_version[0],
			'conformance_test_result': '',  # Only applicable for results
			'cmaf_initialisation_constraints': self.cmaf_initialisation_constraints[0]
		}
	
	def json_analysis(self):
		return {
			'switching_set_id': self.switching_set_id,
			'test_stream_ids': self.test_stream_ids[1],
			'test_file_paths': self.test_file_paths[1],
			'mezzanine_version': self.mezzanine_version[1],
			'conformance_test_result': '',  # Only applicable for results
			'cmaf_initialisation_constraints': self.cmaf_initialisation_constraints[1]
		}
	
	def json_res(self):
		return {
			'switching_set_id': self.switching_set_id,
			'test_stream_ids': self.test_stream_ids[2],
			'test_file_paths': self.test_file_paths[2],
			'mezzanine_version': self.mezzanine_version[2],
			'conformance_test_result': self.conformance_test_result,
			'cmaf_initialisation_constraints': self.cmaf_initialisation_constraints[2]
		}
	
	def json_full(self):
		return {
			'SwitchingSetValidation': {
				'switching_set_id': self.switching_set_id,
				'test_stream_ids': {
					'expected': self.test_stream_ids[0],
					'detected': self.test_stream_ids[1],
					'test_result': self.test_stream_ids[2]
				},
				'test_file_paths': {
					'expected': self.test_file_paths[0],
					'detected': self.test_file_paths[1],
					'test_result': self.test_file_paths[2]
				},
				'mezzanine_version': {
					'expected': self.mezzanine_version[0],
					'detected': self.mezzanine_version[1],
					'test_result': self.mezzanine_version[2].value
				},
				'conformance_test_result': self.conformance_test_result,
				'cmaf_initialisation_constraints': {
					'expected': self.cmaf_initialisation_constraints[0],
					'detected': self.cmaf_initialisation_constraints[1],
					'test_result': self.cmaf_initialisation_constraints[2].value
				}
			}
		}


# Constants
sep = '/'
TS_START = 'Test stream'
SS_START = '8.5 Switching Set Playback'
TS_DEFINITION_ROW_OFFSET = 3  # Number of rows from 'Test stream' root to actual definition data
TS_LOCATION_FRAME_RATES_50 = '12.5_25_50'
TS_LOCATION_FRAME_RATES_59_94 = '14.985_29.97_59.94'
TS_LOCATION_FRAME_RATES_60 = '15_30_60'
TS_LOCATION_SETS_POST = '_sets'
TS_MPD_NAME = 'stream.mpd'
TS_INIT_SEGMENT_NAME = 'init.mp4'
TS_FIRST_SEGMENT_NAME = '0.m4s'
TS_METADATA_POSTFIX = '_info.xml'
SS_NAME = 'ss1'  # For now there is only 1 switching set

# Default codec test content matrix CSV file URLs
MATRIX_AVC = 'https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/export?format=csv'
MATRIX_AVC_FILENAME = 'matrix_avc.csv'

# Dicts
h264_profile = {'66': 'Baseline', '77': 'Main', '88': 'Extended', '100': 'High', '110': 'High 10'}
h264_slice_type = {'0': 'P slice', '1': 'B slice', '2': 'I slice',
				'3': 'SP slice', '4': 'SI slice',
				'5': 'P slice', '6': 'B slice', '7': 'I slice',
				'8': 'SP slice', '9': 'SI slice'}
h265_profile = {'1': 'Main', '2': 'Main 10'}
h265_tier = {'0': 'Main', '1': 'High'}
# For codec_name ffmpeg uses the ISO/IEC MPEG naming convention except for AVC
codec_names = {'h264': 'avc'}  # Convert codec_name using ITU-T naming convention to ISO/IEC MPEG naming convention
cmaf_brand_codecs = {'cfhd': 'avc', 'chdf': 'avc',
					'chh1': 'hevc', 'cud1': 'hevc', 'clg1': 'hevc', 'chd1': 'hevc', 'cdm1': 'hevc', 'cdm4': 'hevc',
					'av01': 'av1', 'cvvc': 'vvc'}  # As defined in CTA-5001-E
frame_rate_group = {12.5: 0.25, 14.985: 0.25, 15: 0.25,
					25: 0.5, 29.97: 0.5, 30: 0.5,
					50: 1, 59.94: 1, 60: 1, 100: 2, 119.88: 2, 120: 2}
frame_rate_value_50 = {0.25: 12.5, 0.5: 25, 1: 50, 2: 100}
frame_rate_value_59_94 = {0.25: 14.985, 0.5: 29.97, 1: 59.94, 2: 119.88}
frame_rate_value_60 = {0.25: 15, 0.5: 30, 1: 60, 2: 120}

# Test results
TS_RESULTS_TOTAL_PASS = 0
TS_RESULTS_TOTAL_FAIL = 0
TS_RESULTS_TOTAL_NOT_TESTABLE = 0
TS_RESULTS_TOTAL_NOT_TESTED = 0
TS_RESULTS_TOTAL_NOT_APPLICABLE = 0
TS_CONFORMANCE_TOTAL_PASS = 0
TS_CONFORMANCE_TOTAL_FAIL = 0
TS_CONFORMANCE_TOTAL_UNKNOWN = 0

# DASH conformance tool
CONFORMANCE_TOOL_DOCKER_CONTAINER_ID = ''

# HTTP server configuration
DETECTED_IP = '127.0.0.1'
PORT = 9090
HTTPD_PATH = ''

# Default parameter values
mezzanine_version = 1


def check_and_analyse_v(test_content, tc_vectors_folder, frame_rate_family, debug_folder):
	global TS_RESULTS_TOTAL_PASS
	global TS_RESULTS_TOTAL_FAIL
	global TS_RESULTS_TOTAL_NOT_TESTABLE
	global TS_RESULTS_TOTAL_NOT_TESTED
	global TS_RESULTS_TOTAL_NOT_APPLICABLE
	global TS_CONFORMANCE_TOTAL_PASS
	global TS_CONFORMANCE_TOTAL_FAIL
	global TS_CONFORMANCE_TOTAL_UNKNOWN
	
	if frame_rate_family not in [TS_LOCATION_FRAME_RATES_50, TS_LOCATION_FRAME_RATES_59_94, TS_LOCATION_FRAME_RATES_60]:
		return
	
	for tc in test_content:
		test_stream_dir = Path(str(tc_vectors_folder)+sep+tc.file_brand[0]+TS_LOCATION_SETS_POST+sep
							+ frame_rate_family+sep+'t'+tc.test_stream_id+sep)
		
		if os.path.isdir(test_stream_dir):
			print("Found test stream folder \""+str(test_stream_dir)+"\"...")
			date_dirs = next(os.walk(str(test_stream_dir)))[1]
			if len(date_dirs) > 0:
				date_dirs.sort()
				most_recent_date = date_dirs[len(date_dirs)-1]
			else:
				tc.test_file_path = 'release (YYYY-MM-DD) folder missing'
				print('No test streams releases found for '+'t'+tc.test_stream_id+'.')
				print()
				continue
			test_stream_date_dir = Path(str(test_stream_dir)+sep+most_recent_date+sep)
			if os.path.isdir(test_stream_date_dir):
				print(str(test_stream_date_dir)+' OK')
			else:
				tc.test_file_path = 'release (YYYY-MM-DD) folder missing'
				print('Test stream folder \"'+str(test_stream_date_dir)+'\" does not exist.')
				print()
				continue
			test_stream_path = Path(str(test_stream_date_dir)+sep+TS_MPD_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path)+' OK')
				tc.test_file_path = str(test_stream_path)
			else:
				tc.test_file_path = TS_MPD_NAME+' file missing'
				print(str(test_stream_path)+' does not exist.')
				print()
				continue
			test_stream_path = Path(str(test_stream_date_dir)+sep+'1'+sep+TS_INIT_SEGMENT_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path)+' OK')
			else:
				tc.test_file_path = TS_INIT_SEGMENT_NAME+' file missing'
				print(str(test_stream_path)+' does not exist.')
				print()
				continue
			test_stream_path = Path(str(test_stream_date_dir)+sep+'1'+sep+TS_FIRST_SEGMENT_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path)+" OK")
				tc.test_file_path = str(test_stream_date_dir)
			else:
				tc.test_file_path = TS_FIRST_SEGMENT_NAME+' file missing'
				print(str(test_stream_path)+' does not exist.')
				print()
				continue
			# Necessary files are present, run analysis
			analyse_stream(tc, frame_rate_family, debug_folder)
		else:
			tc.test_file_path = 'folder missing'
			print('Test stream folder \"'+str(test_stream_dir)+'\" does not exist.')
			print()
		
		# Count results
		if tc.conformance_test_result != '':
			if tc.conformance_test_result['verdict'] == 'PASS':
				TS_CONFORMANCE_TOTAL_PASS += 1
			elif tc.conformance_test_result['verdict'] == 'FAIL':
				TS_CONFORMANCE_TOTAL_FAIL += 1
			else:
				TS_CONFORMANCE_TOTAL_UNKNOWN += 1
		else:
			TS_CONFORMANCE_TOTAL_UNKNOWN += 1
		for a, v in tc.__dict__.items():
			if len(v) == 3:
				if v[2] == TestResult.PASS:
					TS_RESULTS_TOTAL_PASS += 1
	
				elif v[2] == TestResult.FAIL:
					TS_RESULTS_TOTAL_FAIL += 1
	
				elif v[2] == TestResult.NOT_TESTED:
					TS_RESULTS_TOTAL_NOT_TESTED += 1
	
				elif v[2] == TestResult.NOT_TESTABLE:
					TS_RESULTS_TOTAL_NOT_TESTABLE += 1
	
				elif v[2] == TestResult.NOT_APPLICABLE:
					TS_RESULTS_TOTAL_NOT_APPLICABLE += 1
	
	# Save metadata to JSON file
	tc_res_filepath = Path(str(tc_matrix.stem)+'_'+frame_rate_family+'_test_results_'+time_of_analysis+'.json')
	tc_res_file = open(str(tc_res_filepath), "w")
	for tc in test_content:
		json.dump(tc, tc_res_file, indent=4, cls=TestContentFullEncoder)
		tc_res_file.write('\n')
	tc_res_file.close()
	
	print("### SUMMARY OF TEST RESULTS:")
	print("#  ")
	print("#  DASH conformance check using https://github.com/Dash-Industry-Forum/DASH-IF-Conformance")
	print("#  CLI: php Process_cli.php --cmaf --ctawave --segments <MPD location>")
	print("#  - Total Conformance Pass: " + str(TS_CONFORMANCE_TOTAL_PASS))
	print("#  - Total Conformance Fail: " + str(TS_CONFORMANCE_TOTAL_FAIL))
	print("#  - Total Conformance Unknown: " + str(TS_CONFORMANCE_TOTAL_UNKNOWN))
	print("#  ")
	print("#  WAVE test content definition conformance check:")
	print("#  - Total Pass: "+str(TS_RESULTS_TOTAL_PASS))
	print("#  - Total Fail: "+str(TS_RESULTS_TOTAL_FAIL))
	print("#  - Total Not Tested: "+str(TS_RESULTS_TOTAL_NOT_TESTED))
	print("#  - Total Not Testable: "+str(TS_RESULTS_TOTAL_NOT_TESTABLE))
	print("#  - Total Not Applicable: "+str(TS_RESULTS_TOTAL_NOT_APPLICABLE))
	print()

	print("Test results stored in: "+str(tc_res_filepath))
	print()


def check_and_analyse_ss(ss_test_content, tc_vectors_folder, frame_rate_family, tc_codec):
	global TS_RESULTS_TOTAL_PASS
	global TS_RESULTS_TOTAL_FAIL
	global TS_RESULTS_TOTAL_NOT_TESTABLE
	global TS_RESULTS_TOTAL_NOT_TESTED
	global TS_RESULTS_TOTAL_NOT_APPLICABLE
	global TS_CONFORMANCE_TOTAL_PASS
	global TS_CONFORMANCE_TOTAL_FAIL
	global TS_CONFORMANCE_TOTAL_UNKNOWN
	
	if frame_rate_family not in [TS_LOCATION_FRAME_RATES_50, TS_LOCATION_FRAME_RATES_59_94, TS_LOCATION_FRAME_RATES_60]:
		return
		
	# Print switching set id
	print('## Testing ' + ss_test_content.switching_set_id)
	
	# Extract necessary data from MPD
	print('Extracting metadata from MPD...')
	mpd_info = etree.parse(str(Path(str(tc_vectors_folder) + sep + tc_codec + '_' + frame_rate_family + '_' + SS_NAME + '_' + TS_MPD_NAME)))
	mpd_info_root = mpd_info.getroot()
	mpd_representations = [element.get("id") for element in mpd_info_root.iter('{*}Representation')]
	mpd_representations = sorted(mpd_representations, key=lambda x: x.split('/')[2])
	print()
	
	if len(mpd_representations) > len(ss_test_content.test_stream_ids[0]):
		ss_test_content.test_stream_ids[2] = TestResult.FAIL \
		+ ' (too many representations: ' + str(len(mpd_representations)) \
		+ ' where ' + str(len(ss_test_content.test_stream_ids[0])) + ' expected)'
	
	# Check mezzanine version
	try:
		ss_test_content.mezzanine_version[1] = float(mpd_info_root[0][1].text.split(' ')[2])
		ss_test_content.mezzanine_version[2] = TestResult.PASS \
			if (ss_test_content.mezzanine_version[0] == ss_test_content.mezzanine_version[1]) \
			else TestResult.FAIL
	except ValueError:
		ss_test_content.mezzanine_version[1] = 'not found where expected in MPD ('+mpd_info_root[0][1].text+')'
		ss_test_content.mezzanine_version[2] = TestResult.UNKNOWN
		raise
	
	# TODO: Check switching set init constraints
	
	for i, tc_id in enumerate(ss_test_content.test_stream_ids[0]):
		if tc_id == '':
			ss_test_content.test_stream_ids[2][i] = TestResult.UNKNOWN
		elif 't'+tc_id in mpd_representations[i].split('/'):
			idx = mpd_representations[i].split('/').index('t'+tc_id)
			ss_test_content.test_stream_ids[1][i] = mpd_representations[i].split('/')[idx][1:]
			ss_test_content.test_stream_ids[2][i] = TestResult.PASS
		else:
			ss_test_content.test_stream_ids[2][i] = TestResult.FAIL
		
		test_stream_dir = Path(str(tc_vectors_folder) + sep + mpd_representations[i] + sep)
		ss_test_content.test_file_paths[0][i] = str(test_stream_dir)
		print("Expected test stream folder based on MPD: ")
		print(str(test_stream_dir))
		
		if os.path.isdir(test_stream_dir):
			print("Found test stream folder \"" + str(test_stream_dir) + "\"...")
			date_dirs = next(os.walk(str(test_stream_dir)))[1]
			if len(date_dirs) > 0:
				date_dirs.sort()
				most_recent_date = date_dirs[len(date_dirs) - 1]
			else:
				ss_test_content.test_file_paths[1][i] = 'release (YYYY-MM-DD) folder missing'
				ss_test_content.test_file_paths[2][i] = TestResult.FAIL
				print('No test streams releases found for ' + 't' + tc_id + '.')
				print()
				continue
			test_stream_date_dir = Path(str(test_stream_dir) + sep + most_recent_date + sep)
			if os.path.isdir(test_stream_date_dir):
				print(str(test_stream_date_dir) + ' OK')
			else:
				ss_test_content.test_file_paths[1][i] = 'release (YYYY-MM-DD) folder missing'
				ss_test_content.test_file_paths[2][i] = TestResult.FAIL
				print('Test stream folder \"' + str(test_stream_date_dir) + '\" does not exist.')
				print()
				continue
			test_stream_path = Path(str(test_stream_date_dir) + sep + TS_MPD_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path) + ' OK')
				ss_test_content.test_file_paths[1][i] = str(test_stream_path)
			else:
				ss_test_content.test_file_paths[1][i] = TS_MPD_NAME + ' file missing'
				ss_test_content.test_file_paths[2][i] = TestResult.FAIL
				print(str(test_stream_path) + ' does not exist.')
				print()
				continue
			test_stream_path = Path(str(test_stream_date_dir) + sep + '1' + sep + TS_INIT_SEGMENT_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path) + ' OK')
			else:
				ss_test_content.test_file_paths[1][i] = TS_INIT_SEGMENT_NAME + ' file missing'
				ss_test_content.test_file_paths[2][i] = TestResult.FAIL
				print(str(test_stream_path) + ' does not exist.')
				print()
				continue
			test_stream_path = Path(str(test_stream_date_dir) + sep + '1' + sep + TS_FIRST_SEGMENT_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path) + " OK")
				print()
				ss_test_content.test_file_paths[1][i] = str(test_stream_date_dir)
				if ss_test_content.test_file_paths[0][i] == ss_test_content.test_file_paths[1][i]:
					ss_test_content.test_file_paths[2][i] = TestResult.PASS
				else:
					ss_test_content.test_file_paths[2][i] = TestResult.FAIL
					print('Incorrect test stream path.')
					print()
			else:
				ss_test_content.test_file_paths[1][i] = TS_FIRST_SEGMENT_NAME + ' file missing'
				ss_test_content.test_file_paths[2][i] = TestResult.FAIL
				print(str(test_stream_path) + ' does not exist.')
				print()
				continue
			# Copy analysis result for this test vector
			# ss_test_content.test_stream_validation_results[i]
		else:
			ss_test_content.test_file_paths[1][i] = 'folder missing'
			ss_test_content.test_file_paths[2][i] = TestResult.FAIL
			print('Test stream folder \"' + str(test_stream_dir) + '\" does not exist.')
			print()
	
	# TODO: Perform conformance test
	
	# Count results
	if ss_test_content.conformance_test_result != '':
		if ss_test_content.conformance_test_result['verdict'] == 'PASS':
			TS_CONFORMANCE_TOTAL_PASS += 1
		elif ss_test_content.conformance_test_result['verdict'] == 'FAIL':
			TS_CONFORMANCE_TOTAL_FAIL += 1
		else:
			TS_CONFORMANCE_TOTAL_UNKNOWN += 1
	else:
		TS_CONFORMANCE_TOTAL_UNKNOWN += 1
	for a, v in ss_test_content.__dict__.items():
		if len(v) == 3:
			if isinstance(v[0], list):
				for i in range(0, len(v[0])):
					if v[2][i] == TestResult.PASS:
						TS_RESULTS_TOTAL_PASS += 1
	
					elif v[2][i] == TestResult.FAIL:
						TS_RESULTS_TOTAL_FAIL += 1
	
					elif v[2][i] == TestResult.NOT_TESTED:
						TS_RESULTS_TOTAL_NOT_TESTED += 1
	
					elif v[2][i] == TestResult.NOT_TESTABLE:
						TS_RESULTS_TOTAL_NOT_TESTABLE += 1
	
					elif v[2][i] == TestResult.NOT_APPLICABLE:
						TS_RESULTS_TOTAL_NOT_APPLICABLE += 1
			else:
				if v[2] == TestResult.PASS:
					TS_RESULTS_TOTAL_PASS += 1
				
				elif v[2] == TestResult.FAIL:
					TS_RESULTS_TOTAL_FAIL += 1
				
				elif v[2] == TestResult.NOT_TESTED:
					TS_RESULTS_TOTAL_NOT_TESTED += 1
				
				elif v[2] == TestResult.NOT_TESTABLE:
					TS_RESULTS_TOTAL_NOT_TESTABLE += 1
				
				elif v[2] == TestResult.NOT_APPLICABLE:
					TS_RESULTS_TOTAL_NOT_APPLICABLE += 1

	# Save metadata to JSON file
	tc_res_filepath = Path(
		str(tc_matrix.stem) + '_' + frame_rate_family + '_test_results_' + time_of_analysis + '.json')
	tc_res_file = open(str(tc_res_filepath), "a")
	json.dump(ss_test_content, tc_res_file, indent=4, cls=TestContentFullEncoder)
	tc_res_file.write('\n')
	tc_res_file.close()

	print("### SUMMARY OF TEST RESULTS:")
	print("#  ")
	print("#  DASH conformance check using https://github.com/Dash-Industry-Forum/DASH-IF-Conformance")
	print("#  CLI: php Process_cli.php --cmaf --ctawave --segments <MPD location>")
	print("#  - Total Conformance Pass: " + str(TS_CONFORMANCE_TOTAL_PASS))
	print("#  - Total Conformance Fail: " + str(TS_CONFORMANCE_TOTAL_FAIL))
	print("#  - Total Conformance Unknown: " + str(TS_CONFORMANCE_TOTAL_UNKNOWN))
	print("#  ")
	print("#  WAVE test content definition conformance check:")
	print("#  - Total Pass: " + str(TS_RESULTS_TOTAL_PASS))
	print("#  - Total Fail: " + str(TS_RESULTS_TOTAL_FAIL))
	print("#  - Total Not Tested: " + str(TS_RESULTS_TOTAL_NOT_TESTED))
	print("#  - Total Not Testable: " + str(TS_RESULTS_TOTAL_NOT_TESTABLE))
	print("#  - Total Not Applicable: " + str(TS_RESULTS_TOTAL_NOT_APPLICABLE))
	print()

	print("Test results stored in: " + str(tc_res_filepath))
	print()
	

def analyse_stream(test_content, frame_rate_family, debug_folder):
	# Print test content id
	print('## Testing t'+test_content.test_stream_id)
	
	if CONFORMANCE_TOOL_DOCKER_CONTAINER_ID != '':
		# Run DASH conformance tool
		# Examples:
		# Using remote server: docker exec -w /var/www/html/Utils/ 164bd9ff5c45 php Process_cli.php --cmaf --ctawave --segments
		# https://dash.akamaized.net/WAVE/vectors/development/cfhd_sets/15_30_60/t1/2022-10-17/stream.mpd
		# Using local server: docker exec -w /var/www/html/Utils/ 164bd9ff5c45 php Process_cli.php --cmaf --ctawave --segments
		# http://127.0.0.1:9090/vectors/development/cfhd_sets/15_30_60/t1/2022-10-17/stream.mpd
		
		# Determine HTTP location of MPD based on file path
		# TEMPORARY bypass using Akamai server for segment validation:
		conformance_http_location = 'https://dash.akamaized.net/WAVE/vectors/development/'+str(Path(test_content.test_file_path+sep+TS_MPD_NAME))[len(HTTPD_PATH):].replace('\\', '/')
		#conformance_http_location = 'http://'+DETECTED_IP+':'+str(PORT)+str(Path(test_content.test_file_path+sep+TS_MPD_NAME))[len(HTTPD_PATH):].replace('\\', '/')
		
		print('Run DASH conformance tool: '+conformance_http_location)
		# --segments disabled due to bug https://github.com/Dash-Industry-Forum/DASH-IF-Conformance/issues/604
		# which causes the DASH-IF conformance tool to enter into an infinite loop incorrectly requesting the
		# same segment (0.m4s) when used specifically with the Python HTTP server
		ct_cli = ['docker', 'exec', '-w', '/var/www/html/Utils/', CONFORMANCE_TOOL_DOCKER_CONTAINER_ID,
			 'php', 'Process_cli.php', '--cmaf', '--ctawave', '--segments', conformance_http_location]
		if sys.platform == "win32":
			ct_cli.insert(0, 'wsl')
		conformance_tool_output = subprocess.check_output(ct_cli)
		
		json_conformance_tool_output = json.loads(conformance_tool_output)
		
		# Anonymize IP in results
		json_conformance_tool_output['source'] = \
			json_conformance_tool_output['source'].replace(json_conformance_tool_output['source'][:json_conformance_tool_output['source'].find(":",5)],'http://localhost')
		
		test_content.conformance_test_result = json_conformance_tool_output
		print("DASH conformance test result: "+json_conformance_tool_output['verdict'])
	
	# Read initial properties using ffprobe: codec name, sample entry / FourCC, resolution
	source_videoproperties = subprocess.check_output(
		['ffprobe', '-i', str(Path(test_content.test_file_path+sep+'1'+sep+TS_INIT_SEGMENT_NAME)),
		'-show_streams', '-select_streams', 'v', '-loglevel', '0', '-print_format', 'json'])
	source_videoproperties_json = json.loads(source_videoproperties)
	test_content.codec_name[1] = codec_names.get(source_videoproperties_json['streams'][0]['codec_name'], source_videoproperties_json['streams'][0]['codec_name'])
	if test_content.codec_name[0] == '':
		test_content.codec_name[2] = TestResult.UNKNOWN
	else:
		test_content.codec_name[2] = TestResult.PASS \
			if (test_content.codec_name[0].replace('.', '').lower() == test_content.codec_name[1].replace('.', '').lower()) \
			else TestResult.FAIL
	print('Codec = '+test_content.codec_name[1])
	
	test_content.sample_entry_type[1] = source_videoproperties_json['streams'][0]['codec_tag_string']
	if test_content.sample_entry_type[0] == '':
		test_content.sample_entry_type[2] = TestResult.UNKNOWN
	else:
		test_content.sample_entry_type[2] = TestResult.PASS \
			if (test_content.sample_entry_type[0].lower() == test_content.sample_entry_type[1].lower()) \
			else TestResult.FAIL
	print('Sample Entry Type = '+source_videoproperties_json['streams'][0]['codec_tag_string'])
	
	test_content.resolution[1].horizontal = source_videoproperties_json['streams'][0]['width']
	test_content.resolution[1].vertical = source_videoproperties_json['streams'][0]['height']
	if test_content.resolution[0].horizontal == 0 or test_content.resolution[0].vertical == 0:
		test_content.resolution[2] = TestResult.UNKNOWN
	else:
		test_content.resolution[2] = TestResult.PASS \
			if (test_content.resolution[0].horizontal == test_content.resolution[1].horizontal
				and test_content.resolution[0].vertical == test_content.resolution[1].vertical) \
			else TestResult.FAIL
	print('Resolution = '
		+ str(source_videoproperties_json['streams'][0]['width'])
		+ 'x' + str(source_videoproperties_json['streams'][0]['height']))
	
	# Read detailed properties using ffmpeg
	ffmpeg_cl = ['ffmpeg',
		'-i', str(Path(test_content.test_file_path+sep+TS_MPD_NAME)),
		'-c', 'copy',
		'-bsf:v', 'trace_headers',
		'-f', 'null', '-']
	
	print('Running ffmpeg trace_headers on full stream...')
	with open(str(Path(str(tc_matrix.stem)+'_trace_headers_init_'+time_of_analysis+'.txt')), "w") as report_file:
		subprocess.run(ffmpeg_cl, stderr=report_file)
	report_file.close()
	
	# Init variables for temp data from file
	file_vui_timing_num_units_in_tick = 0
	file_vui_timing_time_scale = 0
	file_frame_rate = ''
	file_duration = ''
	file_codec_profile = ''
	file_codec_tier = ''
	file_codec_level = ''
	file_chunks_per_fragment = 0
	h264_detected = False
	h265_detected = False
	sps_detected = False
	sps_processed = False
	file_sps_count = 0
	file_pps_count = 0
	vui_detected = False
	sei_detected = False
	pic_timing_sei_detected = False
	last_nal_unit_type = 0
	nal_slice_types = []

	# Open ffmpeg trace_headers output for analysis
	headers_trace_file = open(str(Path(str(tc_matrix.stem)+'_trace_headers_init_'+time_of_analysis+'.txt')), encoding="utf-8")
	headers_trace = headers_trace_file.readlines()
	print('Checking ffmpeg trace_headers log...')
	nb_lines = len(headers_trace)
	for n, line in enumerate(headers_trace):
		if h264_detected:
			# Tier is not applicable
			test_content.codec_tier[2] = TestResult.NOT_APPLICABLE
			
			if sps_detected and not sps_processed:
				if line.__contains__(' profile_idc '):
					file_codec_profile = line.split(' = ')[1][:-1]
					test_content.codec_profile[1] = h264_profile.get(file_codec_profile, '')
					if test_content.codec_profile[0] == '':
						test_content.codec_profile[2] = TestResult.UNKNOWN
					else:
						test_content.codec_profile[2] = TestResult.PASS \
							if (test_content.codec_profile[0].lower() == test_content.codec_profile[1].lower()) \
							else TestResult.FAIL
					print('Profile = '+test_content.codec_profile[1])
					continue
					
				if line.__contains__(' level_idc '):
					file_codec_level = line.split(' = ')[1][:-1]
					test_content.codec_level[1] = str(eval(file_codec_level+"/10"))
					if test_content.codec_level[0] == '':
						test_content.codec_level[2] = TestResult.UNKNOWN
					else:
						test_content.codec_level[2] = TestResult.PASS \
							if (float(test_content.codec_level[0]) == float(test_content.codec_level[1])) \
							else TestResult.FAIL
					print('Level = '+test_content.codec_level[1])
					continue
					
				if not vui_detected and line.__contains__(' vui_parameters_present_flag ') and line.endswith('= 1\n'):
					vui_detected = True
					print('VUI present')
					continue
				if vui_detected:
					if line.__contains__(' timing_info_present_flag ') and line.endswith('= 1\n'):
						test_content.vui_timing_present[1] = True
						if test_content.vui_timing_present[0] == '':
							test_content.vui_timing_present[2] = TestResult.UNKNOWN
						else:
							test_content.vui_timing_present[2] = TestResult.PASS \
								if (test_content.vui_timing_present[0] is test_content.vui_timing_present[1]) \
								else TestResult.FAIL
						continue
					if line.__contains__(' timing_info_present_flag ') and line.endswith('= 0\n'):
						test_content.vui_timing_present[1] = False
						if test_content.vui_timing_present[0] == '':
							test_content.vui_timing_present[2] = TestResult.UNKNOWN
						else:
							test_content.vui_timing_present[2] = TestResult.PASS \
								if (test_content.vui_timing_present[0] is test_content.vui_timing_present[1]) \
								else TestResult.FAIL
						sps_processed = True
						continue
						
					if test_content.vui_timing_present[1] and line.__contains__(' num_units_in_tick '):
						file_vui_timing_num_units_in_tick = int(line.split(' = ')[1])
						continue
					if test_content.vui_timing_present[1] and line.__contains__(' time_scale '):
						file_vui_timing_time_scale = int(line.split(' = ')[1])
						print('VUI timing present')
						vui_file_frame_rate = float(Decimal(file_vui_timing_time_scale/file_vui_timing_num_units_in_tick/2).quantize(Decimal('.001'), rounding=ROUND_DOWN))
						if frame_rate_group.get(vui_file_frame_rate):
							if str(vui_file_frame_rate)[-2:] == '.0':
								vui_file_frame_rate = int(vui_file_frame_rate)
							test_content.frame_rate[1] = vui_file_frame_rate
						else:
							test_content.frame_rate[1] = \
								'invalid VUI timing data (fps='+str(vui_file_frame_rate)+') | ffmpeg detected frame rate = ' \
								+ str(file_frame_rate)+'('+str(frame_rate_group.get(file_frame_rate, '?')) + ')'
						# The frame rate is already adapted based on the frame rate family when this log occurs
						# Determine the test result for the frame rate
						if test_content.frame_rate[0] == 0:
							test_content.frame_rate[2] = TestResult.UNKNOWN
						else:
							test_content.frame_rate[2] = TestResult.PASS \
								if (test_content.frame_rate[0] == test_content.frame_rate[1]) \
								else TestResult.FAIL
						print('VUI frame rate = '+str(vui_file_frame_rate))
						sps_processed = True
						continue
			
			if sei_detected:
				if pic_timing_sei_detected:
					if line.__contains__(' pic_struct '):
						print('Picture timing SEI pic_struct='+(line.split(' = ')[1]))
						continue
				elif line.startswith('[trace_headers') and line.endswith('] Picture Timing\n'):
					pic_timing_sei_detected = True
					print('Picture timing SEI present')
					test_content.picture_timing_sei_present[1] = True
					if test_content.picture_timing_sei_present[0] == '':
						test_content.picture_timing_sei_present[2] = TestResult.UNKNOWN
					else:
						test_content.picture_timing_sei_present[2] = TestResult.PASS \
							if (test_content.picture_timing_sei_present[0] is
								test_content.picture_timing_sei_present[1]) \
							else TestResult.FAIL
					continue
			
			if line.__contains__(' nal_unit_type '):
				last_nal_unit_type = int(line.split(' = ')[1][:-1])
				continue
			if line.__contains__(' slice_type '):
				nal_slice_types.append([last_nal_unit_type, int(line.split(' = ')[1][:-1])])
				continue
			if line.startswith('[trace_headers'):
				if line.endswith('] Sequence Parameter Set\n'):
					file_sps_count += 1
					if not sps_processed:
						sps_detected = True
				elif line.endswith('] Picture Parameter Set\n'):
					file_pps_count += 1
				elif line.endswith('] Supplemental Enhancement Information\n'):
					sei_detected = True
		
		elif h265_detected:
			if sps_detected and not sps_processed:
				if line.__contains__(' general_tier_flag '):
					file_codec_tier = line.split(' = ')[1]
					test_content.codec_tier[1] = h265_tier.get(file_codec_tier, '')
					if test_content.codec_tier[0] == '':
						test_content.codec_tier[2] = TestResult.UNKNOWN
					else:
						test_content.codec_tier[2] = TestResult.PASS \
							if (test_content.codec_tier[0].lower() == test_content.codec_tier[1].lower()) \
							else TestResult.FAIL
					print('Tier = '+file_codec_tier)
					continue
					
				if line.__contains__(' general_profile_idc '):
					file_codec_profile = line.split(' = ')[1]
					test_content.codec_profile[1] = h265_profile.get(file_codec_profile, '')
					if test_content.codec_profile[0] == '':
						test_content.codec_profile[2] = TestResult.UNKNOWN
					else:
						test_content.codec_profile[2] = TestResult.PASS \
							if (test_content.codec_profile[0].lower() == test_content.codec_profile[1].lower()) \
							else TestResult.FAIL
					print('Profile = '+file_codec_profile)
					continue
					
				if line.__contains__(' general_level_idc '):
					file_codec_level = line.split(' = ')[1]
					test_content.codec_level[1] = str(eval(file_codec_level+"/30"))
					if test_content.codec_level[0] == '':
						test_content.codec_level[2] = TestResult.UNKNOWN
					else:
						test_content.codec_level[2] = TestResult.PASS \
							if (float(test_content.codec_level[0]) == float(test_content.codec_level[1])) \
							else TestResult.FAIL
					print('Level = '+file_codec_level)
					continue
					
				if not vui_detected and line.__contains__(' vui_parameters_present_flag ') and line.endswith('= 1\n'):
					vui_detected = True
					print('VUI present')
					continue
				if vui_detected:
					if line.__contains__(' vui_timing_info_present_flag ') and line.endswith('= 1\n'):
						test_content.vui_timing_present[1] = True
						if test_content.vui_timing_present[0] == '':
							test_content.vui_timing_present[2] = TestResult.UNKNOWN
						else:
							test_content.vui_timing_present[2] = TestResult.PASS \
								if (test_content.vui_timing_present[0] is test_content.vui_timing_present[1]) \
								else TestResult.FAIL
						continue
					if line.__contains__(' vui_timing_info_present_flag ') and line.endswith('= 0\n'):
						test_content.vui_timing_present[1] = False
						if test_content.vui_timing_present[0] == '':
							test_content.vui_timing_present[2] = TestResult.UNKNOWN
						else:
							test_content.vui_timing_present[2] = TestResult.PASS \
								if (test_content.vui_timing_present[0] is test_content.vui_timing_present[1]) \
								else TestResult.FAIL
						sps_processed = True
						continue
						
					if test_content.vui_timing_present[1] and line.__contains__(' vui_num_units_in_tick '):
						file_vui_timing_num_units_in_tick = int(line.split(' = ')[1])
						continue
					if test_content.vui_timing_present[1] and line.__contains__(' vui_time_scale '):
						file_vui_timing_time_scale = int(line.split(' = ')[1])
						print('VUI timing present')
						vui_file_frame_rate = float(Decimal(file_vui_timing_time_scale/file_vui_timing_num_units_in_tick).quantize(Decimal('.001'), rounding=ROUND_DOWN))
						if frame_rate_group.get(vui_file_frame_rate):
							if str(vui_file_frame_rate)[-2:] == '.0':
								vui_file_frame_rate = int(vui_file_frame_rate)
							test_content.frame_rate[1] = vui_file_frame_rate
						else:
							test_content.frame_rate[1] = \
								'invalid VUI timing data (fps='+str(vui_file_frame_rate)+') | ffmpeg detected frame rate = ' \
								+ str(file_frame_rate)+'('+str(frame_rate_group.get(file_frame_rate, '?')) + ')'
						# The frame rate is already adapted based on the frame rate family when this log occurs
						# Determine the test result for the frame rate
						if test_content.frame_rate[0] == 0:
							test_content.frame_rate[2] = TestResult.UNKNOWN
						else:
							test_content.frame_rate[2] = TestResult.PASS \
								if (test_content.frame_rate[0] == test_content.frame_rate[1]) \
								else TestResult.FAIL
						print('VUI frame rate = '+str(vui_file_frame_rate))
						sps_processed = True
						continue
				
			if sei_detected:
				if pic_timing_sei_detected:
					if line.__contains__(' pic_struct '):
						print('Picture timing SEI pic_struct=' + (line.split(' = ')[1]))
						continue
				elif line.startswith('[trace_headers') and line.endswith('] Picture Timing\n'):
					pic_timing_sei_detected = True
					print('Picture timing SEI present')
					test_content.picture_timing_sei_present[1] = True
					if test_content.picture_timing_sei_present[0] == '':
						test_content.picture_timing_sei_present[2] = TestResult.UNKNOWN
					else:
						test_content.picture_timing_sei_present[2] = TestResult.PASS \
							if (test_content.picture_timing_sei_present[0] is
								test_content.picture_timing_sei_present[1]) \
							else TestResult.FAIL
					continue
			
			elif line.startswith('[trace_headers'):
				if line.endswith('] Sequence Parameter Set\n'):
					file_sps_count += 1
					if not sps_processed:
						sps_detected = True
				elif line.endswith('] Picture Parameter Set\n'):
					file_pps_count += 1
					sei_detected = True
				elif line.endswith('] Prefix Supplemental Enhancement Information\n'):
					sei_detected = True
		
		if line.startswith('frame='):
			if n == nb_lines-2:
				# Update test results for SEI messages
				if not pic_timing_sei_detected:
					test_content.picture_timing_sei_present[1] = False
					if test_content.picture_timing_sei_present[0] == '':
						test_content.picture_timing_sei_present[2] = TestResult.UNKNOWN
					else:
						test_content.picture_timing_sei_present[2] = TestResult.PASS \
							if (test_content.picture_timing_sei_present[0] is
								test_content.picture_timing_sei_present[1]) \
							else TestResult.FAIL
				
				# Check duration detected by ffmpeg based on total frames (as the time reported never matches total duration)
				file_duration = round(eval(line.split('=')[1].lstrip().split(' ')[0]+'*1/'+str(file_frame_rate)), 3)
				if str(file_duration)[-2:] == '.0':
					file_duration = int(file_duration)
				test_content.duration[1] = file_duration
				if test_content.duration[0] == 0:
					test_content.duration[2] = TestResult.UNKNOWN
				else:
					# Check duration matches target or is less than 1 frame lower than target duration (for fractional frame rates)
					test_content.duration[2] = TestResult.PASS \
						if (test_content.duration[0] >= test_content.duration[1] > (test_content.duration[1] - (1 / file_frame_rate))) \
						else TestResult.FAIL
				print('Duration = '+str(test_content.duration[1])+'s')
			continue
			
		if not h264_detected and not h265_detected and line.__contains__('Stream #0:0'):
			if line.__contains__('/s,'):
				line_data_array = line[:line.find('kb/s,')].split(',')
				if line.__contains__('fps'):
					file_frame_rate = float(line[line.find('kb/s,'):].split(',')[1][:-3])
				if file_frame_rate == 14.99:
					file_frame_rate = 14.985  # Compensate for ffmpeg rounding fps
				if frame_rate_group.get(file_frame_rate):
					if str(file_frame_rate)[-2:] == '.0':
						file_frame_rate = int(file_frame_rate)
					test_content.frame_rate[1] = file_frame_rate
				else:
					test_content.frame_rate[1] = 'ínvalid ffmpeg detected frame rate = ' + str(file_frame_rate)
				# Adapt the frame rate now that we know the frame rate family
				if frame_rate_family == TS_LOCATION_FRAME_RATES_50:
					test_content.frame_rate[0] = frame_rate_value_50.get(test_content.frame_rate[0], 0)
				elif frame_rate_family == TS_LOCATION_FRAME_RATES_59_94:
					test_content.frame_rate[0] = frame_rate_value_59_94.get(test_content.frame_rate[0], 0)
				elif frame_rate_family == TS_LOCATION_FRAME_RATES_60:
					test_content.frame_rate[0] = frame_rate_value_60.get(test_content.frame_rate[0], 0)
				# Determine the test result for the frame rate
				if test_content.frame_rate[0] == 0:
					test_content.frame_rate[2] = TestResult.UNKNOWN
				else:
					test_content.frame_rate[2] = TestResult.PASS \
						if (test_content.frame_rate[0] == test_content.frame_rate[1]) \
						else TestResult.FAIL
				print('ffmpeg detected frame rate = ' + str(file_frame_rate))
				
				test_content.bitrate[1] = int(line_data_array[len(line_data_array)-1])
				if test_content.bitrate[0] == 0:
					test_content.bitrate[2] = TestResult.UNKNOWN
				else:
					test_content.bitrate[2] = TestResult.PASS \
						if (test_content.bitrate[0] == test_content.bitrate[1]) \
						else TestResult.FAIL
				print('Bitrate = '+str(test_content.bitrate[1])+'kb/s')
			if line.__contains__(': Video: h264'):
				h264_detected = True
			elif line.__contains__(': Video: hevc'):
				h265_detected = True
				continue
		if line.__contains__('Invalid data found when processing input'):
			headers_trace_file.close()
			return
		
	headers_trace_file.close()
	
	# Init variables for temp data from file
	mpd_media_presentation_duration = 0
	file_media_presentation_duration = 0
	file_timescale = 0
	file_tot_sample_duration = 0
	file_stream_brands = []
	file_samples_per_chunk = []
	file_chunks_per_fragment_mdat = 0
	file_stream_i_frames = 0
	file_stream_p_frames = 0
	file_stream_b_frames = 0
	file_sample_i_frames = 0
	file_sample_p_frames = 0
	file_sample_b_frames = 0
	
	# Extract necessary data from MPD
	print('Extracting metadata from MPD...')
	mpd_info = etree.parse(str(Path(test_content.test_file_path+sep+TS_MPD_NAME)))
	mpd_info_root = mpd_info.getroot()
	mpd_media_presentation_duration = \
		isodate.parse_duration(mpd_info_root.get("mediaPresentationDuration")).total_seconds()
	try:
		test_content.mezzanine_version[1] = float(mpd_info_root[0][1].text.split(' ')[2])
		test_content.mezzanine_version[2] = TestResult.PASS \
			if (test_content.mezzanine_version[0] == test_content.mezzanine_version[1]) \
			else TestResult.FAIL
	except ValueError:
		test_content.mezzanine_version[1] = 'not found where expected in MPD ('+mpd_info_root[0][1].text+')'
		test_content.mezzanine_version[2] = TestResult.UNKNOWN
		raise
	try:
		# Adapt the frame rate now that we know the frame rate family
		if frame_rate_family == TS_LOCATION_FRAME_RATES_50:
			test_content.mezzanine_format[0] = \
				test_content.mezzanine_format[0].split('@')[0] \
				+ '@' + str(frame_rate_value_50.get(float(test_content.mezzanine_format[0].split('@')[1].split('_')[0]), 'unknown')) \
				+ '_' + test_content.mezzanine_format[0].split('@')[1].split('_')[1]
		elif frame_rate_family == TS_LOCATION_FRAME_RATES_59_94:
			test_content.mezzanine_format[0] = \
				test_content.mezzanine_format[0].split('@')[0] \
				+ '@' + str(frame_rate_value_59_94.get(float(test_content.mezzanine_format[0].split('@')[1].split('_')[0]), 'unknown')) \
				+ '_' + test_content.mezzanine_format[0].split('@')[1].split('_')[1]
		elif frame_rate_family == TS_LOCATION_FRAME_RATES_60:
			test_content.mezzanine_format[0] = \
				test_content.mezzanine_format[0].split('@')[0] \
				+ '@' + str(frame_rate_value_60.get(float(test_content.mezzanine_format[0].split('@')[1].split('_')[0]), 'unknown')) \
				+ '_' + test_content.mezzanine_format[0].split('@')[1].split('_')[1]
		# Construct the string based on MPD.ProgramInformation
		if (str(mpd_media_presentation_duration)[-2:] == '.0') or (str(mpd_media_presentation_duration).split('.')[1].startswith('99')):
			adapted_mpd_media_presentation_duration = round(mpd_media_presentation_duration)
		else:
			adapted_mpd_media_presentation_duration = mpd_media_presentation_duration
		test_content.mezzanine_format[1] = '_'.join(mpd_info_root[0][1].text.split(' ')[0].split('_')[2:3]) \
										+ '_' + str(adapted_mpd_media_presentation_duration)
		# Determine the test result
		test_content.mezzanine_format[2] = TestResult.PASS \
			if (test_content.mezzanine_format[0] == test_content.mezzanine_format[1]) \
			else TestResult.FAIL
	except ValueError:
		test_content.mezzanine_version[1] = 'not found where expected in MPD ('+mpd_info_root[0][1].text+')'
		test_content.mezzanine_version[2] = TestResult.UNKNOWN
		raise
	
	# Use MP4Box to dump IsoMedia file box metadata for analysis
	MP4Box_cl = ['MP4Box',
		str(Path(test_content.test_file_path+sep+'1'+sep+TS_INIT_SEGMENT_NAME)),
		'-diso']
		
	MP4Box_cl2 = ['MP4Box',
		str(Path(test_content.test_file_path+sep+'1'+sep+TS_FIRST_SEGMENT_NAME)),
		'-init-seg', str(Path(test_content.test_file_path+sep+'1'+sep+TS_INIT_SEGMENT_NAME)),
		'-diso']

	print('Running MP4Box to dump IsoMedia file box metadata from init and first segments to XML...')
	subprocess.run(MP4Box_cl)
	subprocess.run(MP4Box_cl2)

	print('Checking IsoMedia file box XML data...')
	mp4_frag_info = etree.parse(str(Path(test_content.test_file_path+sep+'1'+sep+TS_INIT_SEGMENT_NAME.split('.')[0]+TS_METADATA_POSTFIX)))
	mp4_frag_info_root = mp4_frag_info.getroot()
	
	mdhd_timescale = [element.get("TimeScale") for element in mp4_frag_info_root.iter('{*}MediaHeaderBox')]
	if mdhd_timescale:
		if mdhd_timescale[0] is not None:
			file_timescale = int(mdhd_timescale[0])
	
	file_stream_brands += [element.get("MajorBrand") for element in mp4_frag_info_root.iter('{*}FileTypeBox')]
	file_stream_brands += [element.get("AlternateBrand") for element in mp4_frag_info_root.iter('{*}BrandEntry')]
	test_content.file_brand[1] = ','.join(file_stream_brands)
	if test_content.file_brand[0] == '':
		test_content.file_brand[2] = TestResult.UNKNOWN
	else:
		test_content.file_brand[2] = TestResult.PASS \
			if (test_content.file_brand[1].find(test_content.file_brand[0]) > -1) \
			else TestResult.FAIL
	print('File brands = '+test_content.file_brand[1])
	
	if len([element.get("content") for element in mp4_frag_info_root.iter('{*}SequenceParameterSet')]) == 0 \
		and len([element.get("content") for element in mp4_frag_info_root.iter('{*}PictureParameterSet')]) == 0:
		test_content.parameter_sets_in_cmaf_header_present[1] = False
	else:
		test_content.parameter_sets_in_cmaf_header_present[1] = True
	if test_content.parameter_sets_in_cmaf_header_present[0] == '':
		test_content.parameter_sets_in_cmaf_header_present[2] = TestResult.UNKNOWN
	else:
		test_content.parameter_sets_in_cmaf_header_present[2] = TestResult.PASS \
			if (test_content.parameter_sets_in_cmaf_header_present[0] is test_content.parameter_sets_in_cmaf_header_present[1]) \
			else TestResult.FAIL
	print('Parameter sets in CMAF header = '+str(test_content.parameter_sets_in_cmaf_header_present[1]))
	
	mp4_frag_info = etree.parse(str(Path(test_content.test_file_path+sep+'1'+sep+TS_FIRST_SEGMENT_NAME.split('.')[0]+TS_METADATA_POSTFIX)))
	mp4_frag_info_root = mp4_frag_info.getroot()
	file_samples_per_chunk = [element.get("SampleCount") for element in mp4_frag_info_root.iter('{*}TrackRunBox')]
	file_samples_per_fragment = sum(map(int, file_samples_per_chunk))
	file_chunks_per_fragment_mdat = sum(1 for element in mp4_frag_info_root.iter('{*}MediaDataBox'))
	spc_count = Counter(file_samples_per_chunk)
	print(str(file_samples_per_fragment) + ' samples per fragment, composed of:')
	for spc_k, spc_v in spc_count.items():
		print(str(spc_v) + ' chunk(s) with ' + str(spc_k) + ' sample(s)')
	file_chunks_per_fragment = len(file_samples_per_chunk)
	if file_chunks_per_fragment > 1:
		if int(file_samples_per_chunk[0]) == 1:
			test_content.chunks_per_fragment[1] = CmafChunksPerFragment.MULTIPLE_CHUNKS_ARE_SAMPLES
		else:
			test_content.chunks_per_fragment[1] = CmafChunksPerFragment.MULTIPLE
	else:
		test_content.chunks_per_fragment[1] = CmafChunksPerFragment.SINGLE
	if test_content.chunks_per_fragment[0] == 0:
		test_content.chunks_per_fragment[2] = TestResult.UNKNOWN
	else:
		test_content.chunks_per_fragment[2] = TestResult.PASS \
			if (test_content.chunks_per_fragment[0] is test_content.chunks_per_fragment[1]
				and file_chunks_per_fragment == file_chunks_per_fragment_mdat) \
			else TestResult.FAIL
	print('Chunks per fragment = moof='+str(file_chunks_per_fragment)+' mdat='+str(file_chunks_per_fragment_mdat)+' ('+str(test_content.chunks_per_fragment[1].value)+')')
	
	if file_frame_rate != '':
		test_content.cmaf_fragment_duration[1] = \
			round(float(eval(str(file_samples_per_fragment)+'/'+str(file_frame_rate))), 1)
		if test_content.cmaf_fragment_duration[0] == 0:
			test_content.cmaf_fragment_duration[2] = TestResult.UNKNOWN
		else:
			test_content.cmaf_fragment_duration[2] = TestResult.PASS \
				if (test_content.cmaf_fragment_duration[0] == test_content.cmaf_fragment_duration[1]) \
				else TestResult.FAIL
		print('Fragment duration = '+str(test_content.cmaf_fragment_duration[1])+' seconds')
		if test_content.cmaf_fragment_duration[1] != 0:
			print('Number of fragments = '+str(int(eval(str(test_content.duration[1])+'/'+str(test_content.cmaf_fragment_duration[1])))))
		else:
			print('Number of fragments = cannot be computed (cmaf_fragment_duration[1] equals 0)')
	else:
		test_content.cmaf_fragment_duration[2] = TestResult.NOT_TESTABLE
	
	# Cursory check that all fragments are present
	nb_fragment_files_found = 0
	stream_folder_contents = os.listdir(str(Path(test_content.test_file_path+sep+'1'+sep)))
	for item in stream_folder_contents:
		if item.endswith('.m4s'):
			nb_fragment_files_found += 1
	print('Found '+str(nb_fragment_files_found)+' fragment m4s files')
	
	# Check frame types (I/P/B) present in stream
	j = 0
	for ntype, stype in nal_slice_types:
		if stype == 2 or stype == 7:
			file_stream_i_frames += 1
		elif stype == 0 or stype == 5:
			file_stream_p_frames += 1
		elif stype == 1 or stype == 6:
			file_stream_b_frames += 1
		# Check frame types (I/P/B) present in first fragment if frame rate known
		if file_frame_rate != '':
			if j < (test_content.cmaf_fragment_duration[1]*file_frame_rate):
				if stype == 2 or stype == 7:
					file_sample_i_frames += 1
				elif stype == 0 or stype == 5:
					file_sample_p_frames += 1
				elif stype == 1 or stype == 6:
					file_sample_b_frames += 1
				j += 1
		
	print('Stream i-frames = '+str(file_stream_i_frames))
	print('Stream p-frames = '+str(file_stream_p_frames))
	print('Stream b-frames = '+str(file_stream_b_frames))
	if file_frame_rate != '':
		print('First fragment i-frames = '+str(file_sample_i_frames))
		print('First fragment p-frames = '+str(file_sample_p_frames))
		print('First fragment b-frames = '+str(file_sample_b_frames))
	
	if file_stream_b_frames > 0:
		test_content.b_frames_present[1] = True
	else:
		test_content.b_frames_present[1] = False
	if test_content.b_frames_present[0] == '':
		test_content.b_frames_present[2] = TestResult.UNKNOWN
	if test_content.b_frames_present[0] == TestResult.NOT_APPLICABLE:
		test_content.b_frames_present[2] = TestResult.NOT_APPLICABLE
	else:
		test_content.b_frames_present[2] = TestResult.PASS \
			if (test_content.b_frames_present[0] is test_content.b_frames_present[1]) \
			else TestResult.FAIL
	
	# In-band parameter sets
	print('First fragment in-band parameter sets (SPS) = '
		+ str(file_sps_count-1)+'/'+str(file_samples_per_fragment)+' frames')
	print('First fragment in-band parameter sets (PPS) = '
		+ str(file_pps_count-1)+'/'+str(file_samples_per_fragment)+' frames')
	
	if file_sps_count > 1 or file_pps_count > 1:
		test_content.parameter_sets_in_band_present[1] = True
	else:
		test_content.parameter_sets_in_band_present[1] = False
		
	if test_content.parameter_sets_in_band_present[0] == '':
		test_content.parameter_sets_in_band_present[2] = TestResult.UNKNOWN
	else:
		test_content.parameter_sets_in_band_present[2] = TestResult.PASS \
			if (test_content.parameter_sets_in_band_present[0] is test_content.parameter_sets_in_band_present[1]) \
			else TestResult.FAIL
	
	# Verify MPD and segment duration are valid
	print('Extracting SampleDuration from every TrackFragmentHeaderBox... ', end='', flush=True)
	seg_files = os.listdir(str(Path(test_content.test_file_path + sep + '1' + sep)))
	for m4s in seg_files:
		if m4s.endswith('.m4s'):
			# Avoid re-exporting the first segment's metadata
			if not os.path.isfile(str(Path(
				test_content.test_file_path + sep + '1' + sep + m4s.split('.')[
					0] + TS_METADATA_POSTFIX))):
				MP4Box_cl3 = ['MP4Box',
						  str(Path(test_content.test_file_path + sep + '1' + sep + m4s)),
						  '-init-seg', str(Path(test_content.test_file_path + sep + '1' + sep + TS_INIT_SEGMENT_NAME)),
						  '-diso']
				# print('Running MP4Box to dump IsoMedia file box metadata from segment to XML...')
				subprocess.run(MP4Box_cl3)
			mp4_frag_info = etree.parse(str(Path(
				test_content.test_file_path + sep + '1' + sep + m4s.split('.')[
					0] + TS_METADATA_POSTFIX)))
			mp4_frag_info_root = mp4_frag_info.getroot()
			tfhd_s_durations = [element.get("SampleDuration") for element in mp4_frag_info_root.iter('{*}TrackFragmentHeaderBox')]
			trun_s_count = [element.get("SampleCount") for element in mp4_frag_info_root.iter('{*}TrackRunBox')]
			for tfhd_sd, trun_sc in zip(tfhd_s_durations, trun_s_count):
				file_tot_sample_duration += int(tfhd_sd)*int(trun_sc)/int(file_timescale)
			
	if test_content.mpd_sample_duration_delta[0] == '':
		test_content.mpd_sample_duration_delta[2] = TestResult.UNKNOWN
	else:
		# Adapt the frame rate now that we know the frame rate family
		# Expect delta between MPD mediaPresentationDuration and total sample duration to be less than the duration of 1 frame
		mpd_sample_duration_delta_expected = 0
		if frame_rate_family == TS_LOCATION_FRAME_RATES_50:
			mpd_sample_duration_delta_expected = round(1 / frame_rate_value_50.get(
				1 / test_content.mpd_sample_duration_delta[0]), 4)
			test_content.mpd_sample_duration_delta[0] = '<' + str(mpd_sample_duration_delta_expected)
		elif frame_rate_family == TS_LOCATION_FRAME_RATES_59_94:
			mpd_sample_duration_delta_expected = round(1 / frame_rate_value_59_94.get(
				1 / test_content.mpd_sample_duration_delta[0]), 4)
			test_content.mpd_sample_duration_delta[0] = '<' + str(mpd_sample_duration_delta_expected)
		elif frame_rate_family == TS_LOCATION_FRAME_RATES_60:
			mpd_sample_duration_delta_expected = round(1 / frame_rate_value_60.get(
				1 / test_content.mpd_sample_duration_delta[0]), 4)
			test_content.mpd_sample_duration_delta[0] = '<' + str(mpd_sample_duration_delta_expected)
		# Save result
		test_content.mpd_sample_duration_delta[1] = round(abs(file_tot_sample_duration - mpd_media_presentation_duration), 4)
		# Determine test result
		test_content.mpd_sample_duration_delta[2] = TestResult.PASS \
			if (mpd_sample_duration_delta_expected > test_content.mpd_sample_duration_delta[1]) \
			else TestResult.FAIL
		
	print("Done")
	print("Total sample duration = "+str(file_tot_sample_duration))
	print("MPD mediaPresentationDuration = "+str(mpd_media_presentation_duration))
	
	# If debug enabled, copy all detailed log files to a folder and zip for analysis
	if debug_folder != '':
		# Zip
		debugz_file = str(Path('tcval_logs_' + time_of_analysis + '.zip'))
		if not os.path.isfile(debugz_file):
			debugz = zipfile.ZipFile(debugz_file, 'w', zipfile.ZIP_DEFLATED)
		else:
			debugz = zipfile.ZipFile(debugz_file, 'a', zipfile.ZIP_DEFLATED)
		
		try:
			tc_file_path_parts = Path(test_content.test_file_path).parts
			path2filename = str(Path("_".join(tc_file_path_parts[len(tc_file_path_parts)-4:]) + '_trace_headers_init_' + time_of_analysis + '.txt'))
			debug_filename = str(Path(debug_folder+sep+path2filename))
			shutil.copy2(str(Path(str(tc_matrix.stem) + '_trace_headers_init_' + time_of_analysis + '.txt')), debug_filename)
			debugz.write(debug_filename, path2filename)
		except OSError as e:
			if e.errno != errno.ENOENT:  # No such file or directory
				raise
		try:
			tc_file_path_parts = Path(test_content.test_file_path + sep + '1').parts
			path2filename = str(Path("_".join(tc_file_path_parts[len(tc_file_path_parts)-5:]) + '_' + TS_INIT_SEGMENT_NAME.split('.')[0] + TS_METADATA_POSTFIX))
			debug_filename = str(Path(debug_folder + sep + path2filename))
			shutil.copy2(str(Path(test_content.test_file_path+sep+'1'+sep+TS_INIT_SEGMENT_NAME.split('.')[0]+TS_METADATA_POSTFIX)), debug_filename)
			debugz.write(debug_filename, path2filename)
		except OSError as e:
			if e.errno != errno.ENOENT:  # No such file or directory
				raise
		
		for m4s in seg_files:
			if m4s.endswith('.m4s'):
				try:
					tc_file_path_parts = Path(test_content.test_file_path + sep + '1').parts
					path2filename = str(Path(
						"_".join(tc_file_path_parts[len(tc_file_path_parts)-5:]) + '_' + m4s.split('.')[0] + TS_METADATA_POSTFIX))
					debug_filename = str(Path(debug_folder + sep + path2filename))
					shutil.copy2(str(Path(test_content.test_file_path+sep+'1'+sep+m4s.split('.')[0]+TS_METADATA_POSTFIX)), debug_filename)
					debugz.write(debug_filename, path2filename)
				except OSError as e:
					if e.errno != errno.ENOENT:  # No such file or directory
						raise
		debugz.close()
		
		# Remove detailed logs now that the zip has been created
		try:
			tc_file_path_parts = Path(test_content.test_file_path).parts
			path2filename = str(Path("_".join(tc_file_path_parts[len(tc_file_path_parts) - 4:]) + '_trace_headers_init_' + time_of_analysis + '.txt'))
			os.remove(str(Path(debug_folder + sep + path2filename)))
		except OSError as e:
			if e.errno != errno.ENOENT:  # No such file or directory
				raise
		try:
			tc_file_path_parts = Path(test_content.test_file_path + sep + '1').parts
			path2filename = str(Path(
				"_".join(tc_file_path_parts[len(tc_file_path_parts) - 5:]) + '_' + TS_INIT_SEGMENT_NAME.split('.')[
					0] + TS_METADATA_POSTFIX))
			os.remove(str(Path(debug_folder + sep + path2filename)))
		except OSError as e:
			if e.errno != errno.ENOENT:  # No such file or directory
				raise
		for m4s in seg_files:
			if m4s.endswith('.m4s'):
				try:
					tc_file_path_parts = Path(test_content.test_file_path + sep + '1').parts
					path2filename = str(Path(
						"_".join(tc_file_path_parts[len(tc_file_path_parts) - 5:]) + '_' + m4s.split('.')[
							0] + TS_METADATA_POSTFIX))
					os.remove(str(Path(debug_folder + sep + path2filename)))
				except OSError as e:
					if e.errno != errno.ENOENT:  # No such file or directory
						raise
	
	# Remove log files created by ffmpeg and MP4Box
	try:
		os.remove(str(Path(str(tc_matrix.stem)+'_trace_headers_init_'+time_of_analysis+'.txt')))
	except OSError as e:
		if e.errno != errno.ENOENT:		# No such file or directory
			raise
	try:
		os.remove(str(Path(test_content.test_file_path+sep+'1'+sep+TS_INIT_SEGMENT_NAME.split('.')[0]+TS_METADATA_POSTFIX)))
	except OSError as e:
		if e.errno != errno.ENOENT:		# No such file or directory
			raise
	
	for m4s in seg_files:
		if m4s.endswith('.m4s'):
			try:
				os.remove(str(Path(test_content.test_file_path+sep+'1'+sep+m4s.split('.')[0]+TS_METADATA_POSTFIX)))
			except OSError as e:
				if e.errno != errno.ENOENT:		# No such file or directory
					raise
	
	print()


if __name__ == "__main__":
	# Check FFMPEG, FFPROBE and GPAC(MP4Box) are installed
	if shutil.which('ffmpeg') is None:
		sys.exit("FFMPEG was not found, ensure FFMPEG is added to the system PATH or is in the same folder as this script.")
	if shutil.which('ffprobe') is None:
		sys.exit("FFMPEG was not found, ensure FFPROBE is added to the system PATH or is in the same folder as this script.")
	if shutil.which('MP4Box') is None:
		sys.exit("MP4Box was not found, ensure MP4Box is added to the system PATH or is in the same folder as this script.")
	
	# Attempt to discover IP address (default)
	DETECTED_IP = socket.gethostbyname(socket.gethostname())
	
	# Basic argument handling
	parser = argparse.ArgumentParser(description="WAVE Mezzanine Test Vector Content Options Validator.")
	
	parser.add_argument(
		'-m', '--matrix',
		required=False,
		help="Specifies a CSV or Excel file that contains the test content matrix, "
			"with the expected content options for each test stream. "
			"(Default: downloads latest matrix CSV for AVC from Google Docs here: "+MATRIX_AVC+").")
		
	parser.add_argument(
		'-v', '--vectors',
		required=True,
		help="Folder containing subfolders with sets of test vectors for a specific codec e.g. \"cfhd_sets\", "
			"that contain subfolders for each frame rate family e.g. \"15_30_60\", "
			"that contain subfolders t1 .. tN with the test vectors to validate. "
			"Example of path to test vector MPD: <vectors>/cfhd_sets/15_30_60/t1/2022-09-23/stream.mpd")
	
	parser.add_argument(
		'--mezzanineversion',
		required=True,
		help="Mezzanine release version expected to be used as the test vector source. Example: 4")
	
	parser.add_argument(
		'--ip',
		required=False,
		help="IP of the local machine that the DASH conformance tool running in Docker should connect to. "
			"Default: auto detected ("+DETECTED_IP+")")
	
	parser.add_argument(
		'-d', '--docker',
		required=False,
		help="ID of Docker container running DASH conformance tool image. Default: disabled")
	
	parser.add_argument(
		'--debug',
		required=False,
		nargs='*',
		help="Preserves logs from ffmpeg and GPAC for analysis as tcval_logs_<date_time>.zip")
	
	args = parser.parse_args()
	
	tc_matrix = ''
	if args.matrix is not None:
		tc_matrix = Path(args.matrix)
	else:
		http_request = urllib.request.Request(url=MATRIX_AVC, unverifiable=True)
		req_file = urllib.request.urlopen(http_request, timeout=10)
		tc_matrix = Path(MATRIX_AVC_FILENAME)
		tc_matrix_file = open(str(tc_matrix), 'wb').write(req_file.read())
	
	tc_vectors_folder = ''
	if args.vectors is not None:
		tc_vectors_folder = Path(args.vectors)
	
	HTTPD_PATH = str(tc_vectors_folder)
	
	if args.docker is not None:
		if all(char in string.hexdigits for char in args.docker):
			CONFORMANCE_TOOL_DOCKER_CONTAINER_ID = args.docker
		else:
			print("Ignoring Docker container ID because it's not a valid hex string: "+args.docker)
	
	# Check CSV matrix file exists
	if not os.path.isfile(tc_matrix):
		sys.exit("Test content matrix file \""+str(tc_matrix)+"\" does not exist.")
		
	# Check vectors folder exists
	if not os.path.isdir(tc_vectors_folder):
		sys.exit("Test vectors folder \""+str(tc_vectors_folder)+"\" does not exist")
	
	# Check mezzanine version can be parsed as a positive number
	mezzanine_version = 1
	try:
		mezzanine_version = float(args.mezzanineversion)
		if mezzanine_version < 1:
			raise ValueError('Expected a positive mezzanine release version of 1 or higher.')
	except ValueError:
		sys.exit("Mezzanine version \"" + str(args.mezzanineversion) + "\" is not a positive number.")
	
	# Check debug folder can be created
	debug_folder = ''
	if args.debug is not None:
		debug_folder = str(Path(str(Path(__file__).resolve().parent)+sep+"tcval_logs"))
		print(debug_folder)
		try:
			if not os.path.isdir(debug_folder):
				os.mkdir(debug_folder)
		except OSError:
			print("Failed to create the directory for the debug files.")
	
	time_of_analysis = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	
	# IP address that will be used
	if args.ip is not None:
		try:
			socket.inet_aton(args.ip)
			local_ip = args.ip
		except socket.error:
			sys.exit('Invalid IP entered:'+str(args.ip))
	else:
		local_ip = DETECTED_IP
	print("IP address: " + local_ip)
	bg_httpd_process = ''
	
	# Ensure Docker container is running and serve test vectors folder
	if CONFORMANCE_TOOL_DOCKER_CONTAINER_ID != '':
		print("Ensuring Docker container is running...")
		ds_cli = ['docker', 'start', CONFORMANCE_TOOL_DOCKER_CONTAINER_ID]
		if sys.platform == "win32":
			ds_cli.insert(0, 'wsl')
		subprocess.run(ds_cli)
		# TODO: Remove this when JCCP validator is fixed
		print("Only content present here will be validated using the JCCP validation tool: https://dash.akamaized.net/WAVE/vectors/development/, \n"
			  "due to bug https://github.com/Dash-Industry-Forum/DASH-IF-Conformance/issues/648")
		# print("Starting HTTP server...")
		# bg_httpd_process_err_log = open("bg_httpd_stderr.log", "wb", 0)
		# bg_httpd_process = subprocess.Popen(["python", "-m", "http.server", str(PORT), "-d", HTTPD_PATH],
		# 									stderr=bg_httpd_process_err_log)
		# print("Waiting 5 seconds for HTTP server to start...")
		# time.sleep(5)
		
	# Read CSV matrix data
	tc_matrix_data = []
	with open(tc_matrix, mode='r') as csv_file:
		csv_data = csv.reader(csv_file)
		for row in csv_data:
			tc_matrix_data.append(row)
	csv_file.close()
	
	# Extract expected test stream parameters
	tc_matrix_ts_start = 0
	tc_matrix_ts_root = [0, 0]
	tc_num_streams = 0
	for i, row in enumerate(tc_matrix_data):
		if TS_START in row:
			tc_matrix_ts_start = row.index(TS_START)
		if tc_matrix_ts_start != 0:
			tc_matrix_ts_root = [i, tc_matrix_ts_start]
			tc_num_streams = len(tc_matrix_data[tc_matrix_ts_root[0]+1][tc_matrix_ts_root[1]:])
			break
	
	test_content = []
	
	for i in range(0, tc_num_streams):
		i_file_brand = tc_matrix_data[tc_matrix_ts_root[0] + TS_DEFINITION_ROW_OFFSET + 11][tc_matrix_ts_root[1] + i]
		
		i_parameter_sets_in_cmaf_header_present = True
		if tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+2][tc_matrix_ts_root[1]+i].find('without parameter sets within the CMAF header') > -1:
			i_parameter_sets_in_cmaf_header_present = False
		
		i_parameter_sets_in_band_present = False
		if tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+2][tc_matrix_ts_root[1]+i].find('in-band parameter sets') > -1:
			i_parameter_sets_in_band_present = True
			
		i_picture_timing_sei_present = False
		if tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET][tc_matrix_ts_root[1]+i] == 'With':
			i_picture_timing_sei_present = True
		
		i_vui_timing_present = False
		if tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+1][tc_matrix_ts_root[1]+i] == 'With':
			i_vui_timing_present = True
			
		i_cmaf_initialisation_constraints = CmafInitConstraints.MULTIPLE
		if tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+4][tc_matrix_ts_root[1]+i].find('Single') > -1:
			i_cmaf_initialisation_constraints = CmafInitConstraints.SINGLE
			
		i_chunks_per_fragment = CmafChunksPerFragment.SINGLE
		if tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+5][tc_matrix_ts_root[1]+i].find('multiple chunks') > -1:
			i_chunks_per_fragment = CmafChunksPerFragment.MULTIPLE
		elif tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+5][tc_matrix_ts_root[1]+i].find('Each sample') > -1:
			i_chunks_per_fragment = CmafChunksPerFragment.MULTIPLE_CHUNKS_ARE_SAMPLES
			
		i_b_frames_present = TestResult.NOT_APPLICABLE
		if tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+5][tc_matrix_ts_root[1]+i].find('p-frame only') > -1:
			i_b_frames_present = False
		elif tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+5][tc_matrix_ts_root[1]+i].find('with b-frames') > -1:
			i_b_frames_present = True
			
		h_res = (lambda x: int(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+6][tc_matrix_ts_root[1]+i].split('x')[0])
				if x.isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+6][tc_matrix_ts_root[1]+i].split('x')[0])
		v_res = (lambda x: int(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+6][tc_matrix_ts_root[1]+i].split('x')[1])
				if x.isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+6][tc_matrix_ts_root[1]+i].split('x')[1])
		i_resolution = VideoResolution(h_res, v_res)
		
		i_frame_rate = (lambda x: float(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+7][tc_matrix_ts_root[1]+i])
				if x.replace(".", "", 1).isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+7][tc_matrix_ts_root[1]+i])
		
		i_duration = (lambda x: int(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+9][tc_matrix_ts_root[1]+i][:-1])
				if x.isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+9][tc_matrix_ts_root[1]+i][:-1])
		
		i_tc = TestContent(tc_matrix_data[tc_matrix_ts_root[0]+1][tc_matrix_ts_root[1]+i],  # test_stream_id
			'',  # test_file_path
			mezzanine_version,  # mezzanine version
			str(h_res)+'x'+str(v_res)+'@'+str(i_frame_rate)+'_'+str(i_duration),  # format as encoded in the mezzanine filename
			'',  # conformance_test_result
			cmaf_brand_codecs.get(i_file_brand, 'unknown'),  # codec_name
			(lambda x: tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')[0]
				if len(x) > 1 else '')(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')),  # codec_profile
			(lambda x: tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')[1]
				if len(x) > 1 else tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i])
						(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')),  # codec_level
			(lambda x: tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')[2]
				if len(x) > 2 else '')(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')),  # codec_tier
			i_file_brand,  # file_brand
			tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+2][tc_matrix_ts_root[1]+i][0:4],  # sample_entry_type
			i_parameter_sets_in_cmaf_header_present,  # parameter_sets_in_cmaf_header_present
			i_parameter_sets_in_band_present,  # parameter_sets_in_band_present
			i_picture_timing_sei_present,  # picture_timing_sei_present
			i_vui_timing_present,  # vui_timing_present
			float(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+3][tc_matrix_ts_root[1]+i]),  # cmaf_fragment_duration in s
			i_cmaf_initialisation_constraints,  # cmaf_initialisation_constraints
			i_chunks_per_fragment,  # chunks_per_fragment
			i_b_frames_present,  # b_frames_present
			i_resolution,  # resolution
			i_frame_rate,  # frame_rate
			(lambda x: int(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+8][tc_matrix_ts_root[1]+i])
				if x.isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+8][tc_matrix_ts_root[1]+i]),  # bit rate in kb/s
			i_duration,  # duration in s
			1/i_frame_rate  # Maximum allowable delta between MPD mediaPresentationDuration and total sample duration
			)
		test_content.append(i_tc)

	# Extract expected switching set parameters
	tc_matrix_ss_start = 0
	tc_matrix_ss_root = [0, 0]
	tc_num_ss_streams = 0
	
	ss_test_content = ''
	ss_test_content_indexes = []

	for i, row in enumerate(tc_matrix_data):
		if SS_START in row:
			tc_matrix_ss_start = row.index(SS_START)
		if tc_matrix_ss_start != 0:
			tc_matrix_ss_root = [i, tc_matrix_ss_start]
			i_ss_tc_id = []
			i_ss_tc_path = []
			i_ss_tc_init_constraints = ''
			i_ss_tc_ts_validation_res = []
			for index, m_item in enumerate(tc_matrix_data[tc_matrix_ss_root[0]][tc_matrix_ss_root[1]:]):
				if m_item == 'X':
					i_ss_tc_id.append(tc_matrix_data[tc_matrix_ts_root[0]+1][index+1])
					for tc_index, tc_item in enumerate(test_content):
						if tc_item.test_stream_id == tc_matrix_data[tc_matrix_ts_root[0]+1][index+1]:
							i_ss_tc_path.append('')
							i_ss_tc_init_constraints = tc_item.cmaf_initialisation_constraints[0]
					ss_test_content_indexes.append([index, tc_matrix_data[tc_matrix_ts_root[0]+1][index+1]])
			ss_test_content = SwitchingSetTestContent(SS_NAME, i_ss_tc_id, i_ss_tc_path, mezzanine_version,
													'', i_ss_tc_init_constraints)
			break

	# Analyse each stream ID and switching set
	tc_copy = copy.deepcopy(test_content)
	check_and_analyse_v(tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_60, debug_folder)
	ss_tc_copy = copy.deepcopy(ss_test_content)
	check_and_analyse_ss(ss_tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_60, test_content[0].codec_name[0])
	
	tc_copy = copy.deepcopy(test_content)
	check_and_analyse_v(tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_59_94, debug_folder)
	ss_tc_copy = copy.deepcopy(ss_test_content)
	check_and_analyse_ss(ss_tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_59_94, test_content[0].codec_name[0])
	
	tc_copy = copy.deepcopy(test_content)
	check_and_analyse_v(tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_50, debug_folder)
	ss_tc_copy = copy.deepcopy(ss_test_content)
	check_and_analyse_ss(ss_tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_50, test_content[0].codec_name[0])

	# Stop serving test vectors folder
	# if CONFORMANCE_TOOL_DOCKER_CONTAINER_ID != '':
		# if bg_httpd_process:
		# 	bg_httpd_process.terminate()
		# bg_httpd_process_err_log.close()

	# Remove debug folder if empty
	if not any(Path(debug_folder).iterdir()):
		try:
			os.rmdir(str(Path(debug_folder)))
		except OSError as e:
			if e.errno != errno.ENOENT:  # No such file or directory
				raise
	