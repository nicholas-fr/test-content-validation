#!/usr/bin/env python3

import argparse
import copy
import csv
import errno
import json
import os
import subprocess
import sys

from datetime import datetime
from decimal import *
from enum import Enum
from json import JSONEncoder
from lxml import etree
from pathlib import Path
from shutil import which


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
	cmaf_initialisation_constraints = ['', '', TestResult.NOT_TESTED]
	chunks_per_fragment = [0, 0, TestResult.NOT_TESTED]
	b_frames_present = ['', '', TestResult.NOT_TESTED]
	resolution = [VideoResolution(), VideoResolution(), TestResult.NOT_TESTED]
	frame_rate = [0.0, 0.0, TestResult.NOT_TESTED]
	bitrate = [0, 0, TestResult.NOT_TESTED]
	duration = [0, 0, TestResult.NOT_TESTED]
	
	def __init__(self, test_stream_id=None, test_file_path=None,
				codec_name=None, codec_profile=None, codec_level=None, codec_tier=None, file_brand=None,
				sample_entry_type=None,	parameter_sets_in_cmaf_header_present=None, parameter_sets_in_band_present=None,
				picture_timing_sei_present=None, vui_timing_present=None,
				cmaf_fragment_duration=None, cmaf_initialisation_constraints=None, chunks_per_fragment=None,
				b_frames_present=None, resolution=None, frame_rate=None, bitrate=None, duration=None):
		if test_stream_id is not None:
			self.test_stream_id = test_stream_id
		if test_file_path is not None:
			self.test_file_path = test_file_path
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
			self.cmaf_initialisation_constraints = [cmaf_initialisation_constraints, '', TestResult.NOT_TESTED]
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

	def json_def(self):
		return {
			'test_stream_id': self.test_stream_id,
			'test_file_path': self.test_file_path,
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
			'duration': self.duration[0]
		}
	
	def json_analysis(self):
		return {
			'test_stream_id': self.test_stream_id,
			'test_file_path': self.test_file_path,
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
			'duration': self.duration[1]
		}
	
	def json_res(self):
		return {
			'test_stream_id': self.test_stream_id,
			'test_file_path': self.test_file_path,
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
			'duration': self.duration[2]
		}
		
	def json_full(self):
		return {
			'TestStreamValidation': {
				'test_stream_id': self.test_stream_id,
				'test_file_path': self.test_file_path,
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


# Constants	
TS_DEFINITION_ROW_OFFSET = 3  # Number of rows from 'Test stream' root to actual definition data
TS_LOCATION_FRAME_RATES_50 = '12.5_25_50'
TS_LOCATION_FRAME_RATES_59_94 = '14.985_29.97_59.94'
TS_LOCATION_FRAME_RATES_60 = '15_30_60'
TS_LOCATION_SETS_POST = '_sets'
TS_MPD_NAME = 'stream.mpd'
TS_INIT_SEGMENT_NAME = 'init.mp4'
TS_FIRST_SEGMENT_NAME = '0.m4s'
TS_METADATA_POSTFIX = '_info.xml'

# Dicts
h264_profile = {'66': 'Baseline', '77': 'Main', '88': 'Extended', '100': 'High', '110': 'High 10'}
h264_slice_type = {'0': 'P slice', '1': 'B slice', '2': 'I slice',
				'3': 'SP slice', '4': 'SI slice',
				'5': 'P slice', '6': 'B slice', '7': 'I slice',
				'8': 'SP slice', '9': 'SI slice'}
h265_profile = {'1': 'Main', '2': 'Main 10'}
h265_tier = {'0': 'Main', '1': 'High'}
frame_rate_group = {12.5: 0.25, 14.985: 0.25, 15: 0.25,
					25: 0.5, 29.97: 0.5, 30: 0.5,
					50: 1, 59.94: 1, 60: 1, 100: 2, 119.88: 2, 120: 2}


def check_and_analyse(test_content, tc_vectors_folder, frame_rate_family):
	if frame_rate_family not in [TS_LOCATION_FRAME_RATES_50, TS_LOCATION_FRAME_RATES_59_94, TS_LOCATION_FRAME_RATES_60]:
		return
	
	for tc in test_content:
		test_stream_dir = Path(str(str(tc_vectors_folder)+'\\'+tc.file_brand[0]+TS_LOCATION_SETS_POST)+'\\'
							+ frame_rate_family+'\\'+'t'+tc.test_stream_id+'\\')
		if os.path.isdir(test_stream_dir):
			print("Found test stream folder \""+str(test_stream_dir)+"\"...")
			date_dirs = next(os.walk(str(test_stream_dir)))[1]
			if len(date_dirs) > 0:
				date_dirs.sort()
				most_recent_date = date_dirs[len(date_dirs)-1]
			else:
				tc.test_file_path = 'release (YYYY-MM-DD) folder missing'
				print('No test streams releases found for '+'t'+tc.test_stream_id+'.')
				continue
			test_stream_date_dir = Path(str(test_stream_dir)+'\\'+most_recent_date+'\\')
			if os.path.isdir(test_stream_date_dir):
				print(str(test_stream_date_dir)+' OK')
			else:
				tc.test_file_path = 'release (YYYY-MM-DD) folder missing'
				print('Test stream folder \"'+str(test_stream_date_dir)+'\" does not exist.')
				continue
			test_stream_path = Path(str(test_stream_date_dir)+'\\'+TS_MPD_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path)+' OK')
				tc.test_file_path = str(test_stream_path)
			else:
				tc.test_file_path = TS_MPD_NAME+' file missing'
				print(str(test_stream_path)+' does not exist.')
				continue
			test_stream_path = Path(str(test_stream_date_dir)+'\\1\\'+TS_INIT_SEGMENT_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path)+' OK')
			else:
				tc.test_file_path = TS_INIT_SEGMENT_NAME+' file missing'
				print(str(test_stream_path)+' does not exist.')
				continue
			test_stream_path = Path(str(test_stream_date_dir)+'\\1\\'+TS_FIRST_SEGMENT_NAME)
			if os.path.isfile(test_stream_path):
				print(str(test_stream_path)+" OK")
				tc.test_file_path = str(test_stream_date_dir)
			else:
				tc.test_file_path = TS_FIRST_SEGMENT_NAME+' file missing'
				print(str(test_stream_path)+' does not exist.')
				continue
			# Necessary files are present, run analysis
			analyse_stream(tc, frame_rate_family)
		else:
			tc.test_file_path = 'folder missing'
			print('Test stream folder \"'+str(test_stream_dir)+'\" does not exist.')
		
	# Save metadata to JSON file
	tc_res_filepath = Path(str(tc_matrix.stem)+'_'+frame_rate_family+'_test_results_'+time_of_analysis+'.json')
	tc_res_file = open(str(tc_res_filepath), "w")
	for tc in test_content:
		json.dump(tc, tc_res_file, indent=4, cls=TestContentFullEncoder)
	tc_res_file.close()

	print("Test results stored in: "+str(tc_res_filepath))
	print()


def analyse_stream(test_content, frame_rate_family):
	# Print test content id
	print('## Testing t'+test_content.test_stream_id)
	
	# Read initial properties using ffprobe: codec name, sample entry / FourCC, resolution
	source_videoproperties = subprocess.check_output(
		['ffprobe', '-i', str(Path(test_content.test_file_path+'\\1\\'+TS_INIT_SEGMENT_NAME)),
		'-show_streams', '-select_streams', 'v', '-loglevel', '0', '-print_format', 'json'])
	source_videoproperties_json = json.loads(source_videoproperties)
	test_content.codec_name[1] = source_videoproperties_json['streams'][0]['codec_name']
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
		'-i', str(Path(test_content.test_file_path+'\\'+TS_MPD_NAME)),
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
	last_nal_unit_type = 0
	nal_slice_types = []

	# Open ffmpeg trace_headers output for analysis
	headers_trace_file = open(str(Path(str(tc_matrix.stem)+'_trace_headers_init_'+time_of_analysis+'.txt')), encoding="utf-8")
	headers_trace = headers_trace_file.readlines()
	print('Checking ffmpeg trace_headers log...')
	for line in headers_trace:
		if h264_detected:
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
						
					if test_content.vui_timing_present[1] and line.__contains__(' num_units_in_tick '):
						file_vui_timing_num_units_in_tick = int(line.split(' = ')[1])
						continue
					if test_content.vui_timing_present[1] and line.__contains__(' time_scale '):
						file_vui_timing_time_scale = int(line.split(' = ')[1])
						print('VUI timing present')
						file_frame_rate = float(Decimal(file_vui_timing_time_scale/file_vui_timing_num_units_in_tick/2).quantize(Decimal('.001'), rounding=ROUND_DOWN))
						test_content.frame_rate[1] = frame_rate_group.get(file_frame_rate, 0)
						if test_content.frame_rate[0] == 0:
							test_content.frame_rate[2] = TestResult.UNKNOWN
						else:
							test_content.frame_rate[2] = TestResult.PASS \
								if (test_content.frame_rate[0] == test_content.frame_rate[1]) \
								else TestResult.FAIL
						print('Frame rate = '+str(file_frame_rate))
						continue
						
					if line.__contains__(' pic_struct_present_flag ') and line.endswith('= 1\n'):
						test_content.picture_timing_sei_present[1] = True
						if test_content.picture_timing_sei_present[0] == '':
							test_content.picture_timing_sei_present[2] = TestResult.UNKNOWN
						else:
							test_content.picture_timing_sei_present[2] = TestResult.PASS \
								if (test_content.picture_timing_sei_present[0] is test_content.picture_timing_sei_present[1]) \
								else TestResult.FAIL
						sps_processed = True
						print('Picture timing SEI present according to VUI (pic_struct_present_flag=1)')
						continue
						
					if line.__contains__(' pic_struct_present_flag ') and line.endswith('= 0\n'):
						test_content.picture_timing_sei_present[1] = False
						if test_content.picture_timing_sei_present[0] == '':
							test_content.picture_timing_sei_present[2] = TestResult.UNKNOWN
						else:
							test_content.picture_timing_sei_present[2] = TestResult.PASS \
								if (test_content.picture_timing_sei_present[0] is test_content.picture_timing_sei_present[1]) \
								else TestResult.FAIL
						sps_processed = True
						print('Picture timing SEI NOT present according to VUI (pic_struct_present_flag=0)')
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
						
					if test_content.vui_timing_present[1] and line.__contains__(' vui_num_units_in_tick '):
						file_vui_timing_num_units_in_tick = int(line.split(' = ')[1])
						continue
					if test_content.vui_timing_present[1] and line.__contains__(' vui_time_scale '):
						file_vui_timing_time_scale = int(line.split(' = ')[1])
						print('VUI timing present')
						file_frame_rate = float(Decimal(file_vui_timing_time_scale/file_vui_timing_num_units_in_tick).quantize(Decimal('.001'), rounding=ROUND_DOWN))
						test_content.frame_rate[1] = frame_rate_group.get(file_frame_rate, 0)
						if test_content.frame_rate[0] == 0:
							test_content.frame_rate[2] = TestResult.UNKNOWN
						else:
							test_content.frame_rate[2] = TestResult.PASS \
								if (test_content.frame_rate[0] == test_content.frame_rate[1]) \
								else TestResult.FAIL
						print('Frame rate = '+str(file_frame_rate))
						continue
						
					if line.__contains__(' frame_field_info_present_flag ') and line.endswith('= 1\n'):
						test_content.picture_timing_sei_present[1] = True
						if test_content.picture_timing_sei_present[0] == '':
							test_content.picture_timing_sei_present[2] = TestResult.UNKNOWN
						else:
							test_content.picture_timing_sei_present[2] = TestResult.PASS \
								if (test_content.picture_timing_sei_present[0] is test_content.picture_timing_sei_present[1]) \
								else TestResult.FAIL
						sps_processed = True
						print('Picture timing SEI present according to VUI (frame_field_info_present_flag=1)')
						continue
						
					if line.__contains__(' frame_field_info_present_flag ') and line.endswith('= 0\n'):
						test_content.picture_timing_sei_present[1] = False
						if test_content.picture_timing_sei_present[0] == '':
							test_content.picture_timing_sei_present[2] = TestResult.UNKNOWN
						else:
							test_content.picture_timing_sei_present[2] = TestResult.PASS \
								if (test_content.picture_timing_sei_present[0] is test_content.picture_timing_sei_present[1]) \
								else TestResult.FAIL
						sps_processed = True
						print('Picture timing SEI NOT present according to VUI (frame_field_info_present_flag=0)')
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
				
		if line.__contains__('Duration: '):
			file_duration = line.split(',')[0].lstrip().split(' ')[1].split('.')[0]
			file_duration_h, file_duration_m, file_duration_s = file_duration.split(':')
			test_content.duration[1] = int(file_duration_h)*3600+int(file_duration_m)*60+int(file_duration_s)
			if test_content.duration[0] == 0:
				test_content.duration[2] = TestResult.UNKNOWN
			else:
				test_content.duration[2] = TestResult.PASS \
					if (test_content.duration[0] == test_content.duration[1]) \
					else TestResult.FAIL
			print('Duration = '+str(test_content.duration[1])+'s')
			continue
			
		if not h264_detected and not h265_detected and line.__contains__('Stream #0:0'):
			if line.__contains__('/s,'):
				line_data_array = line[:line.find('kb/s,')].split(',')
				if line.__contains__('fps'): file_frame_rate = float(line[line.find('kb/s,'):].split(',')[1][:-3])
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
	file_stream_brands = []
	file_samples_per_chunk = []
	file_stream_i_frames = 0
	file_stream_p_frames = 0
	file_stream_b_frames = 0
	file_sample_i_frames = 0
	file_sample_p_frames = 0
	file_sample_b_frames = 0
	
	# Use MP4Box to dump IsoMedia file box metadata for analysis
	MP4Box_cl = ['MP4Box',
		str(Path(test_content.test_file_path+'\\1\\'+TS_INIT_SEGMENT_NAME)),
		'-diso']
		
	MP4Box_cl2 = ['MP4Box',
		str(Path(test_content.test_file_path+'\\1\\'+TS_FIRST_SEGMENT_NAME)),
		'-init-seg', str(Path(test_content.test_file_path+'\\1\\'+TS_INIT_SEGMENT_NAME)),
		'-diso']

	print('Running MP4Box to dump IsoMedia file box metadata from init and first segments to XML...')
	subprocess.run(MP4Box_cl)
	subprocess.run(MP4Box_cl2)

	print('Checking IsoMedia file box XML data...')
	mp4_frag_info = etree.parse(str(Path(test_content.test_file_path+'\\1\\'+TS_INIT_SEGMENT_NAME.split('.')[0]+TS_METADATA_POSTFIX)))
	mp4_frag_info_root = mp4_frag_info.getroot()
	
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
	
	if [element.get("content") for element in mp4_frag_info_root.iter('{*}SequenceParameterSet')][0] is None \
		and [element.get("content") for element in mp4_frag_info_root.iter('{*}PictureParameterSet')][0] is None:
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
	
	mp4_frag_info = etree.parse(str(Path(test_content.test_file_path+'\\1\\'+TS_FIRST_SEGMENT_NAME.split('.')[0]+TS_METADATA_POSTFIX)))
	mp4_frag_info_root = mp4_frag_info.getroot()
	file_samples_per_chunk = [element.get("SampleCount") for element in mp4_frag_info_root.iter('{*}TrackRunBox')]
	print('Samples per chunk = '+file_samples_per_chunk[0])
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
			if (test_content.chunks_per_fragment[0] is test_content.chunks_per_fragment[1]) \
			else TestResult.FAIL
	print('Chunks per fragment = '+str(test_content.chunks_per_fragment[1].value)+' ('+str(file_chunks_per_fragment)+')')
	
	if file_frame_rate != '':
		test_content.cmaf_fragment_duration[1] = int(eval(file_samples_per_chunk[0]+'*'+str(file_chunks_per_fragment)+'/'+str(file_frame_rate)))
		if test_content.cmaf_fragment_duration[0] == 0:
			test_content.cmaf_fragment_duration[2] = TestResult.UNKNOWN
		else:
			test_content.cmaf_fragment_duration[2] = TestResult.PASS \
				if (test_content.cmaf_fragment_duration[0] == test_content.cmaf_fragment_duration[1]) \
				else TestResult.FAIL
		print('Fragment duration = '+str(test_content.cmaf_fragment_duration[1])+' seconds')
		print('Number of fragments = '+str(int(eval(str(test_content.duration[1])+'/'+str(test_content.cmaf_fragment_duration[1])))))
	else:
		test_content.cmaf_fragment_duration[2] = TestResult.NOT_TESTABLE
	
	# Cursory check that all fragments are present
	nb_fragment_files_found = 0
	stream_folder_contents = os.listdir(str(Path(test_content.test_file_path+'\\1\\')))
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
	else:
		test_content.b_frames_present[2] = TestResult.PASS \
			if (test_content.b_frames_present[0] is test_content.b_frames_present[1]) \
			else TestResult.FAIL
	
	# In-band parameter sets
	print('First fragment in-band parameter sets (SPS) = '
		+ str(file_sps_count-1)+'/'+str(eval(file_samples_per_chunk[0]+'*'+str(file_chunks_per_fragment)))+' frames')
	print('First fragment in-band parameter sets (PPS) = '
		+ str(file_pps_count-1)+'/'+str(eval(file_samples_per_chunk[0]+'*'+str(file_chunks_per_fragment)))+' frames')
	
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
	
	# Remove log files created by ffmpeg and MP4Box
	try:
		os.remove(str(Path(str(tc_matrix.stem)+'_trace_headers_init_'+time_of_analysis+'.txt')))
	except OSError as e:
		if e.errno != errno.ENOENT:		# No such file or directory
			raise
	try:
		os.remove(str(Path(test_content.test_file_path+'\\1\\'+TS_INIT_SEGMENT_NAME.split('.')[0]+TS_METADATA_POSTFIX)))
	except OSError as e:
		if e.errno != errno.ENOENT:		# No such file or directory
			raise
	try:
		os.remove(str(Path(test_content.test_file_path+'\\1\\'+TS_FIRST_SEGMENT_NAME.split('.')[0]+TS_METADATA_POSTFIX)))
	except OSError as e:
		if e.errno != errno.ENOENT:		# No such file or directory
			raise
	
	print()


if __name__ == "__main__":
	# Check FFMPEG, FFPROBE and GPAC(MP4Box) are installed
	if which('ffmpeg') is None:
		sys.exit("FFMPEG was not found, ensure FFMPEG is added to the system PATH or is in the same folder as this script.")
	if which('ffprobe') is None:
		sys.exit("FFMPEG was not found, ensure FFPROBE is added to the system PATH or is in the same folder as this script.")
	if which('MP4Box') is None:
		sys.exit("MP4Box was not found, ensure MP4Box is added to the system PATH or is in the same folder as this script.")
	
	# Basic argument handling
	parser = argparse.ArgumentParser(description="WAVE Mezzanine Test Vector Content Options Validator.")
	
	parser.add_argument(
		'-m', '--matrix',
		required=True,
		help="Specifies a CSV or Excel file that contains the test content matrix, with the expected content options for each test stream.")
		
	parser.add_argument(
		'-v', '--vectors',
		required=True,
		help="Folder containing the test vectors to validate.")
		
	args = parser.parse_args()
	
	tc_matrix = ''
	if args.matrix is not None:
		tc_matrix = Path(args.matrix)
	
	tc_vectors_folder = ''
	if args.vectors is not None:
		tc_vectors_folder = Path(args.vectors)
	
	# Check CSV matrix file exists
	if not os.path.isfile(tc_matrix):
		sys.exit("Test content matrix file \""+str(tc_matrix)+"\" does not exist.")
		
	# Check vectors folder exists
	if not os.path.isdir(tc_vectors_folder):
		sys.exit("Test vectors folder \""+str(tc_vectors_folder)+"\" does not exist")
	
	time_of_analysis = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	
	# Read CSV matrix to determine expected streams/values
	tc_matrix_data = []
	with open(tc_matrix, mode ='r') as csv_file:
		csv_data = csv.reader(csv_file)
		for row in csv_data:
			tc_matrix_data.append(row)
	
	tc_matrix_ts_start = 0
	tc_matrix_ts_root = [0, 0]
	tc_num_streams = 0
	for i, row in enumerate(tc_matrix_data):
		if 'Test stream' in row:
			tc_matrix_ts_start = row.index('Test stream')
		if tc_matrix_ts_start != 0:
			tc_matrix_ts_root = [i, tc_matrix_ts_start]
			tc_num_streams = len(tc_matrix_data[tc_matrix_ts_root[0]+1][tc_matrix_ts_root[1]:])
			break
	
	test_content = []
	
	for i in range(0, tc_num_streams):
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
			
		i_b_frames_present = True
		if tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+5][tc_matrix_ts_root[1]+i].find('p-frame only') > -1:
			i_b_frames_present = False
			
		i_resolution = VideoResolution(
			(lambda x: int(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+6][tc_matrix_ts_root[1]+i].split('x')[0])
				if x.isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+6][tc_matrix_ts_root[1]+i].split('x')[0]),
			(lambda x: int(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+6][tc_matrix_ts_root[1]+i].split('x')[1])
				if x.isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+6][tc_matrix_ts_root[1]+i].split('x')[1]))
			
		i_tc = TestContent(tc_matrix_data[tc_matrix_ts_root[0]+1][tc_matrix_ts_root[1]+i],  # test_stream_id
			'',  # test_file_path
			'',  # codec_name
			(lambda x: tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')[0]
				if len(x) > 1 else '')(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')),  # codec_profile
			(lambda x: tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')[1]
				if len(x) > 1 else tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i])
						(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')),  # codec_level
			(lambda x: tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')[2]
				if len(x) > 2 else '')(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+10][tc_matrix_ts_root[1]+i].split(' ')),  # codec_tier
			tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+11][tc_matrix_ts_root[1]+i],  # file_brand
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
			(lambda x: float(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+7][tc_matrix_ts_root[1]+i])
				if x.replace(".", "", 1).isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+7][tc_matrix_ts_root[1]+i]),  # frame_rate
			(lambda x: int(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+8][tc_matrix_ts_root[1]+i])
				if x.isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+8][tc_matrix_ts_root[1]+i]),  # bitrate in kb/s
			(lambda x: int(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+9][tc_matrix_ts_root[1]+i][:-1])
				if x.isdigit() else 0)(tc_matrix_data[tc_matrix_ts_root[0]+TS_DEFINITION_ROW_OFFSET+9][tc_matrix_ts_root[1]+i][:-1]),  # duration in s
			)
		test_content.append(i_tc)
	
	# Analyse each stream ID in matrix
	tc_copy = copy.deepcopy(test_content)
	check_and_analyse(tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_60)
	tc_copy = copy.deepcopy(test_content)
	check_and_analyse(tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_59_94)
	tc_copy = copy.deepcopy(test_content)
	check_and_analyse(tc_copy, tc_vectors_folder, TS_LOCATION_FRAME_RATES_50)
