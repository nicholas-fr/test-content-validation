#!/usr/bin/env python3

import argparse
import json
import os
import sys
import xlsxwriter

from pathlib import Path
from termcolor import cprint


test_info = {0: 'test_stream_id', 1: 'test_file_path'}
tests = {0: 'mezzanine_version', 1: 'mezzanine_format', 2: 'mezzanine_label', 3: 'codec_profile', 4: 'codec_level',
		 5: 'codec_tier', 6: 'file_brand', 7: 'sample_entry_type', 8: 'parameter_sets_in_cmaf_header_present',
		 9: 'parameter_sets_in_band_present', 10: 'picture_timing_sei_present', 11: 'vui_timing_present',
		 12: 'vui_primaries_mcoeffs', 13: 'vui_transfer_characteristics', 14: 'sei_pref_transfer_characteristics',
		 15: 'cmaf_fragment_duration', 16: 'cmaf_initialisation_constraints', 17: 'chunks_per_fragment',
		 18: 'b_frames_present', 19: 'cmf2_sample_flags_present', 20: 'resolution', 21: 'pixel_aspect_ratio',
		 22: 'frame_rate', 23: 'bitrate', 24: 'duration', 25: 'mpd_sample_duration_delta', 26: 'mpd_bitstream_mismatch'}

# Basic argument handling
parser = argparse.ArgumentParser(description="WAVE Validator Results Parser.")
parser.add_argument(
		'-r', '--results',
		required=True,
		help="Specifies a JSON test results file.")
parser.add_argument(
		'-j', '--jccp',
		required=False,
		type=bool,
		help="Indicate whether to include JCCP DASH-IF validator failures in results summary.")
parser.add_argument(
		'-m', '--missing',
		required=False,
		type=bool,
		help="Indicate whether to indicate missing streams in results summary.")
parser.add_argument(
		'-n', '--ntestable',
		required=False,
		type=bool,
		help="Indicate whether to indicate not testable issues in results summary.")

args = parser.parse_args()

res_file = str(Path(args.results).resolve())
# Check JSON results file exists
if not os.path.isfile(res_file):
	sys.exit("Test results file \""+res_file+"\" does not exist.")

try:
	res = open(res_file)
	pl = json.load(res)
except json.JSONDecodeError as e:
	sys.exit("Failed to load JSON results file \"" + str(Path(args.results).resolve()) + "\". Is this a valid JSON file?")
	
#pl_len = len(pl)
os.system("color")
print("WAVE Test Stream Validation Results")
print()
#for i in range(1, pl_len+1):
for i,key in enumerate(pl):
	if ("missing" in key and args.missing) or "missing" not in key:
		print ('## Stream '+str(key)+':  ', end='', flush=True)
		cprint(pl[key]['file_brand']['expected']+' ', 'light_blue', end='', flush=True)
		cprint(pl[key][test_info[0]], 'light_blue')
		if "missing" in key:
			print()
			continue
		if args.jccp:
			if pl[key]['conformance_test_result']['verdict'] == 'FAIL':
				print("Test: {0:40}".format("DASH-IF Conformance tools"), end='', flush=True)
				cprint("FAIL", 'red')
				if len(pl[key]['conformance_test_result'])>1:
					if pl[key]['conformance_test_result']['entries']['Schematron']['verdict'] == 'FAIL':
						print("      > {0:38}".format("Schematron"), end='', flush=True)
						cprint("FAIL", 'red')
					if pl[key]['conformance_test_result']['entries']['MPEG-DASH Common']['verdict'] == 'FAIL':
						print("      > {0:38}".format("MPEG-DASH Common"), end='', flush=True)
						cprint("FAIL", 'red')
					if pl[key]['conformance_test_result']['entries']['CMAF']['verdict'] == 'FAIL':
						print("      > {0:38}".format("CMAF"), end='', flush=True)
						cprint("FAIL", 'red')
					if pl[key]['conformance_test_result']['entries']['CTA-WAVE']['verdict'] == 'FAIL':
						print("      > {0:38}".format("CTA-WAVE"), end='', flush=True)
						cprint("FAIL", 'red')
					if pl[key]['conformance_test_result']['entries']['SEGMENT_VALIDATION']['verdict'] == 'FAIL':
						print("      > {0:38}".format("SEGMENT VALIDATION"), end='', flush=True)
						cprint("FAIL", 'red')
					if pl[key]['conformance_test_result']['entries']['SEGMENT_VALIDATION']['verdict'] == 'WARN':
						print("      > {0:38}".format("SEGMENT VALIDATION"), end='', flush=True)
						cprint("WARNING", 'yellow')
					if pl[key]['conformance_test_result']['entries']['HEALTH']['verdict'] == 'FAIL':
						print("      > {0:38}".format("HEALTH"), end='', flush=True)
						cprint("FAIL", 'red')
		for j,test in tests.items():
			if pl[key][test]['test_result'] == 'FAIL':
				print("Test: {0:40}".format(test), end='', flush=True)
				cprint(pl[key][test]['test_result'],'red', end='', flush=True)
				cprint('\t'+str(pl[key][test]['detected']), 'light_red', end='', flush=True)
				print(' instead of ', end='', flush=True)
				if str(pl[key][test]['expected']) != '':
					cprint(str(pl[key][test]['expected']), 'light_green')
				else:
					print('?')
				
			if pl[key][test]['test_result'] == 'UNKNOWN':
				print("Test: {0:40}".format(test), end='', flush=True)
				cprint(pl[key][test]['test_result'],'yellow', end='', flush=True)
				if str(pl[key][test]['detected']) != '':
					cprint('\t'+str(pl[key][test]['detected']), 'light_yellow', end='', flush=True)
					print(' detected')
				else:
					print('?')
	
			if pl[key][test]['test_result'] == 'NOT TESTED':
				print("Test: {0:40}".format(test), end='', flush=True)
				cprint(pl[key][test]['test_result'],'light_blue', end='', flush=True)
				cprint('\t', 'light_red', end='', flush=True)
				print(' instead of ', end='', flush=True)
				if str(pl[key][test]['expected']) != '':
					cprint(str(pl[key][test]['expected']), 'light_green')
				else:
					print('?')
				
			if pl[key][test]['test_result'] == 'NOT TESTABLE' and args.ntestable:
				print("Test: {0:40}".format(test), end='', flush=True)
				cprint(pl[key][test]['test_result'],'light_blue', end='', flush=True)
				print(' expect ', end='', flush=True)
				cprint(str(pl[key][test]['expected']), 'light_green')
		print()
		print()
	
## Adapt to XLSX
print("Saving as XLSX...", end='', flush=True)
# XLSX format
wb = xlsxwriter.Workbook(str(Path(str(Path(res_file).parent)+'/'+str(Path(res_file).stem)+'.xlsx')))

# Styles
LABEL_WIDTH = 360
RES_WIDTH = 112
ZOOM = 70

style_test_label = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#000000", 'bold': True, 'right': 1})
style_total_label = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#000000", 'bold': True, 'right': 1, 'align': "right"})
style_ftotal_label = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#000000", 'bold': True, 'left': 1, 'align': "left"})
style_stream_label = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#000000", 'bold': True, 'bottom': 1, 'rotation': 30})
style_source = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#000000", 'font_size': 10, 'align': "left", 'align': "top", 'text_wrap': True})
style_default = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#000000"})
style_pass = wb.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
style_fail = wb.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006", 'bold': True})
style_warn = wb.add_format({"bg_color": "#FAF0C6", "font_color": "#9a8219", 'bold': True})
style_unknown = wb.add_format({"bg_color": "#FAF0C6", "font_color": "#9a8219"})
style_not_applicable = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#8dd69c"})
style_not_tested = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#4c50b9"})
style_not_testable = wb.add_format({"bg_color": "#FFFFFF", "font_color": "#000000", 'italic': False})

style_mapping = {'PASS': style_pass, 'FAIL': style_fail, 'UNKNOWN': style_unknown, 'WARN': style_warn,
				 'NOT APPLICABLE': style_not_applicable, 'NOT TESTED': style_not_tested, 'NOT TESTABLE': style_not_testable}

ws = wb.add_worksheet("Results")
ws.set_column_pixels(0, 0, LABEL_WIDTH)
ws.set_column_pixels(1, len(pl), RES_WIDTH)
ws.set_zoom(ZOOM)

# Source file
ws.write(0, 0,str(Path(res_file).name), style_source)

# Add row labels for each test
ws.write(1, 0," > Schematron", style_test_label)
ws.write(2, 0," > MPEG-DASH Common", style_test_label)
ws.write(3, 0," > CMAF", style_test_label)
ws.write(4, 0," > CTA-WAVE", style_test_label)
ws.write(5, 0," > SEGMENT VALIDATION", style_test_label)
ws.write(6, 0," > HEALTH", style_test_label)
ws.write(7, 0,"conformance_test_result", style_test_label)
conformance_offset = 7

for l, test in tests.items():
	ws.write(l + 1 + conformance_offset, 0, test, style_test_label)

num_tests = len(tests.items())
ws.write(num_tests+2+conformance_offset, 0, 'TOTAL PASS: ', style_total_label)
ws.write(num_tests+3+conformance_offset, 0, 'TOTAL FAIL: ', style_total_label)
ws.write(num_tests+4+conformance_offset, 0, 'TOTAL UNKNOWN: ', style_total_label)
ws.write(num_tests+5+conformance_offset, 0, 'TOTAL NOT APPLICABLE: ', style_total_label)
ws.write(num_tests+6+conformance_offset, 0, 'TOTAL NOT TESTED: ', style_total_label)
ws.write(num_tests+7+conformance_offset, 0, 'TOTAL NOT TESTABLE: ', style_total_label)

last_col = 2

# Freeze top row and left column
ws.freeze_panes(1, 1)

# Add results for each test stream validated
for i,key in enumerate(pl):
	# print('## Stream ' + str(i) + ':  ', end='', flush=True)
	# cprint(pl[key]['file_brand']['expected'] + ' ', 'light_blue', end='', flush=True)
	# cprint(pl[key][test_info[0]], 'light_blue')
	ws.write(0, i + 1, key, style_stream_label)
	ws.write(7, i + 1,  pl[key]['conformance_test_result']['verdict'], style_mapping.get(pl[key]['conformance_test_result']['verdict'],style_default))
	if len(pl[key]['conformance_test_result']) > 1:
		ws.write(1, i + 1, pl[key]['conformance_test_result']['entries']['Schematron']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['Schematron']['verdict'], style_default))
		ws.write(2, i + 1, pl[key]['conformance_test_result']['entries']['MPEG-DASH Common']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['MPEG-DASH Common']['verdict'], style_default))
		ws.write(3, i + 1, pl[key]['conformance_test_result']['entries']['CMAF']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['CMAF']['verdict'], style_default))
		ws.write(4, i + 1, pl[key]['conformance_test_result']['entries']['CTA-WAVE']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['CTA-WAVE']['verdict'], style_default))
		ws.write(5, i + 1, pl[key]['conformance_test_result']['entries']['SEGMENT_VALIDATION']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['SEGMENT_VALIDATION']['verdict'], style_default))
		ws.write(6, i + 1, pl[key]['conformance_test_result']['entries']['HEALTH']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['HEALTH']['verdict'], style_default))
	else:
		ws.write(2, i + 1, "NOT TESTED", style_not_tested)
		ws.write(3, i + 1, "NOT TESTED", style_not_tested)
		ws.write(4, i + 1, "NOT TESTED", style_not_tested)
		ws.write(5, i + 1, "NOT TESTED", style_not_tested)
		ws.write(6, i + 1, "NOT TESTED", style_not_tested)
		ws.write(7, i + 1, "NOT TESTED", style_not_tested)
	
	for j, test in tests.items():
		if pl[key][test]['test_result']:
			ws.write(j+1+conformance_offset, i + 1, pl[key][test]['test_result'],
					 style_mapping.get(pl[key][test]['test_result'], style_default))
	
	col_pre = ''
	if (i + 2) > 26:
		col_pre = chr(ord('@') + int((i + 2) / 26))
	col = (lambda x: col_pre + chr(ord('@') + int(x)) if x > 0 else 'Z')((i + 2) % 26)
	last_col = i + 2
	ws.write(num_tests+2+conformance_offset, i + 1, '=COUNTIF('+col+str(2)+',"PASS")+COUNTIF('+col+str(2+conformance_offset)+':'+col+str(num_tests+1+conformance_offset)+',"PASS")', style_pass)
	ws.write(num_tests+3+conformance_offset, i + 1, '=COUNTIF('+col+str(2)+',"FAIL")+COUNTIF('+col+str(2+conformance_offset)+':'+col+str(num_tests+1+conformance_offset)+',"FAIL")', style_fail)
	ws.write(num_tests+4+conformance_offset, i + 1, '=COUNTIF('+col+str(2)+',"UNKNOWN")+COUNTIF('+col+str(2+conformance_offset)+':'+col+str(num_tests+1+conformance_offset)+',"UNKNOWN")', style_unknown)
	ws.write(num_tests+5+conformance_offset, i + 1, '=COUNTIF('+col+str(2)+',"NOT APPLICABLE")+COUNTIF('+col+str(2+conformance_offset)+':'+col+str(num_tests+1+conformance_offset)+',"NOT APPLICABLE")', style_not_applicable)
	ws.write(num_tests+6+conformance_offset, i + 1, '=COUNTIF('+col+str(2)+',"NOT TESTED")+COUNTIF('+col+str(2+conformance_offset)+':'+col+str(num_tests+1+conformance_offset)+',"NOT TESTED")', style_not_tested)
	ws.write(num_tests+7+conformance_offset, i + 1, '=COUNTIF('+col+str(2)+',"NOT TESTABLE")+COUNTIF('+col+str(2+conformance_offset)+':'+col+str(num_tests+1+conformance_offset)+',"NOT TESTABLE")', style_not_testable)


# Add final totals
ws.write(num_tests + 2 + conformance_offset, last_col + 3, 'TOTAL PASS for all streams', style_ftotal_label)
ws.write(num_tests + 3 + conformance_offset, last_col + 3, 'TOTAL FAIL for all streams ', style_ftotal_label)
ws.write(num_tests + 4 + conformance_offset, last_col + 3, 'TOTAL UNKNOWN for all streams', style_ftotal_label)
ws.write(num_tests + 5 + conformance_offset, last_col + 3, 'TOTAL NOT APPLICABLE for all streams', style_ftotal_label)
ws.write(num_tests + 6 + conformance_offset, last_col + 3, 'TOTAL NOT TESTED for all streams', style_ftotal_label)
ws.write(num_tests + 7 + conformance_offset, last_col + 3, 'TOTAL NOT TESTABLE for all streams', style_ftotal_label)

col_pre = ''
if last_col > 26:
	col_pre = chr(ord('@') + int(last_col / 26))
col = (lambda x: col_pre + chr(ord('@') + int(x)) if x > 0 else 'Z')(last_col % 26)
ws.write(num_tests+2+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+2+conformance_offset+1)+':'+col+str(num_tests+2+conformance_offset+1)+')', style_pass)
ws.write(num_tests+3+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+3+conformance_offset+1)+':'+col+str(num_tests+3+conformance_offset+1)+')', style_fail)
ws.write(num_tests+4+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+4+conformance_offset+1)+':'+col+str(num_tests+4+conformance_offset+1)+')', style_unknown)
ws.write(num_tests+5+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+5+conformance_offset+1)+':'+col+str(num_tests+5+conformance_offset+1)+')', style_not_applicable)
ws.write(num_tests+6+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+6+conformance_offset+1)+':'+col+str(num_tests+6+conformance_offset+1)+')', style_not_tested)
ws.write(num_tests+7+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+7+conformance_offset+1)+':'+col+str(num_tests+7+conformance_offset+1)+')', style_not_testable)

# Collapse DASH JCCP validator results
ws.set_row(1, None, None, {'level': 1, 'hidden': True})
ws.set_row(2, None, None, {'level': 1, 'hidden': True})
ws.set_row(3, None, None, {'level': 1, 'hidden': True})
ws.set_row(4, None, None, {'level': 1, 'hidden': True})
ws.set_row(5, None, None, {'level': 1, 'hidden': True})
ws.set_row(6, None, None, {'level': 1, 'hidden': True})
ws.set_row(7, None, None, {'collapsed': True})



# Add detailed results sheet (same as results + info about failures)
ws = wb.add_worksheet("Detailed Results")
ws.set_column_pixels(0, 0, LABEL_WIDTH)
ws.set_column_pixels(1, len(pl), RES_WIDTH)
ws.set_zoom(ZOOM)

# Source file
ws.write(0, 0,str(Path(res_file).name), style_source)

# Add row labels for each test
ws.write(1, 0," > Schematron", style_test_label)
ws.write(2, 0," > MPEG-DASH Common", style_test_label)
ws.write(3, 0," > CMAF", style_test_label)
ws.write(4, 0," > CTA-WAVE", style_test_label)
ws.write(5, 0," > SEGMENT VALIDATION", style_test_label)
ws.write(6, 0," > HEALTH", style_test_label)
ws.write(7, 0,"conformance_test_result", style_test_label)
conformance_offset = 7

for l, test in tests.items():
	ws.write(l + 1 + conformance_offset, 0, test, style_test_label)

num_tests = len(tests.items())
ws.write(num_tests+2+conformance_offset, 0, 'TOTAL PASS: ', style_total_label)
ws.write(num_tests+3+conformance_offset, 0, 'TOTAL FAIL: ', style_total_label)
ws.write(num_tests+4+conformance_offset, 0, 'TOTAL UNKNOWN: ', style_total_label)
ws.write(num_tests+5+conformance_offset, 0, 'TOTAL NOT APPLICABLE: ', style_total_label)
ws.write(num_tests+6+conformance_offset, 0, 'TOTAL NOT TESTED: ', style_total_label)
ws.write(num_tests+7+conformance_offset, 0, 'TOTAL NOT TESTABLE: ', style_total_label)

# Freeze top row and left column
ws.freeze_panes(1, 1)

# Add name and results of each test stream validated
for i,key in enumerate(pl):
	# print('## Stream ' + str(i) + ':  ', end='', flush=True)
	# cprint(pl[key]['file_brand']['expected'] + ' ', 'light_blue', end='', flush=True)
	# cprint(pl[key][test_info[0]], 'light_blue')
	ws.write(0, i + 1, key, style_stream_label)
	ws.write(7, i + 1,  pl[key]['conformance_test_result']['verdict'], style_mapping.get(pl[key]['conformance_test_result']['verdict'],style_default))
	if len(pl[key]['conformance_test_result']) > 1:
		ws.write(1, i + 1, pl[key]['conformance_test_result']['entries']['Schematron']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['Schematron']['verdict'], style_default))
		ws.write(2, i + 1, pl[key]['conformance_test_result']['entries']['MPEG-DASH Common']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['MPEG-DASH Common']['verdict'], style_default))
		ws.write(3, i + 1, pl[key]['conformance_test_result']['entries']['CMAF']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['CMAF']['verdict'], style_default))
		ws.write(4, i + 1, pl[key]['conformance_test_result']['entries']['CTA-WAVE']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['CTA-WAVE']['verdict'], style_default))
		ws.write(5, i + 1, pl[key]['conformance_test_result']['entries']['SEGMENT_VALIDATION']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['SEGMENT_VALIDATION']['verdict'], style_default))
		ws.write(6, i + 1, pl[key]['conformance_test_result']['entries']['HEALTH']['verdict'],
				 style_mapping.get(pl[key]['conformance_test_result']['entries']['HEALTH']['verdict'], style_default))
	else:
		ws.write(2, i + 1, "NOT TESTED", style_not_tested)
		ws.write(3, i + 1, "NOT TESTED", style_not_tested)
		ws.write(4, i + 1, "NOT TESTED", style_not_tested)
		ws.write(5, i + 1, "NOT TESTED", style_not_tested)
		ws.write(6, i + 1, "NOT TESTED", style_not_tested)
		ws.write(7, i + 1, "NOT TESTED", style_not_tested)
	
	for j, test in tests.items():
		if pl[key][test]['test_result']:
			if pl[key][test]['test_result'] == 'FAIL':
				ws.write(j+1+conformance_offset, i + 1, pl[key][test]['test_result']+' ('+str(pl[key][test]['detected'])+'  instead of  '+str(pl[key][test]['expected'])+')',
					 	style_mapping.get(pl[key][test]['test_result'], style_default))
			else:
				ws.write(j+1+conformance_offset, i + 1, pl[key][test]['test_result'],
					 	style_mapping.get(pl[key][test]['test_result'], style_default))
	col_pre = ''
	if (i + 2) > 26:
		col_pre = chr(ord('@') + int((i + 2) / 26))
	col = (lambda x: col_pre + chr(ord('@') + int(x)) if x > 0 else 'Z')((i + 2) % 26)
	ws.write(num_tests+2+conformance_offset, i + 1, '=Results!'+col+str(num_tests+3+conformance_offset), style_pass)
	ws.write(num_tests+3+conformance_offset, i + 1, '=Results!'+col+str(num_tests+4+conformance_offset), style_fail)
	ws.write(num_tests+4+conformance_offset, i + 1, '=Results!'+col+str(num_tests+5+conformance_offset), style_unknown)
	ws.write(num_tests+5+conformance_offset, i + 1, '=Results!'+col+str(num_tests+6+conformance_offset), style_not_applicable)
	ws.write(num_tests+6+conformance_offset, i + 1, '=Results!'+col+str(num_tests+7+conformance_offset), style_not_tested)
	ws.write(num_tests+7+conformance_offset, i + 1, '=Results!'+col+str(num_tests+8+conformance_offset), style_not_testable)

# Add final totals
ws.write(num_tests + 2 + conformance_offset, last_col + 3, 'TOTAL PASS for all streams', style_ftotal_label)
ws.write(num_tests + 3 + conformance_offset, last_col + 3, 'TOTAL FAIL for all streams ', style_ftotal_label)
ws.write(num_tests + 4 + conformance_offset, last_col + 3, 'TOTAL UNKNOWN for all streams', style_ftotal_label)
ws.write(num_tests + 5 + conformance_offset, last_col + 3, 'TOTAL NOT APPLICABLE for all streams', style_ftotal_label)
ws.write(num_tests + 6 + conformance_offset, last_col + 3, 'TOTAL NOT TESTED for all streams', style_ftotal_label)
ws.write(num_tests + 7 + conformance_offset, last_col + 3, 'TOTAL NOT TESTABLE for all streams', style_ftotal_label)

col_pre = ''
if last_col > 26:
	col_pre = chr(ord('@') + int(last_col / 26))
col = (lambda x: col_pre + chr(ord('@') + int(x)) if x > 0 else 'Z')(last_col % 26)
ws.write(num_tests+2+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+2+conformance_offset+1)+':'+col+str(num_tests+2+conformance_offset+1)+')', style_pass)
ws.write(num_tests+3+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+3+conformance_offset+1)+':'+col+str(num_tests+3+conformance_offset+1)+')', style_fail)
ws.write(num_tests+4+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+4+conformance_offset+1)+':'+col+str(num_tests+4+conformance_offset+1)+')', style_unknown)
ws.write(num_tests+5+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+5+conformance_offset+1)+':'+col+str(num_tests+5+conformance_offset+1)+')', style_not_applicable)
ws.write(num_tests+6+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+6+conformance_offset+1)+':'+col+str(num_tests+6+conformance_offset+1)+')', style_not_tested)
ws.write(num_tests+7+conformance_offset, last_col + 2, '=SUM(B'+str(num_tests+7+conformance_offset+1)+':'+col+str(num_tests+7+conformance_offset+1)+')', style_not_testable)

# Collapse DASH JCCP validator results
ws.set_row(1, None, None, {'level': 1, 'hidden': True})
ws.set_row(2, None, None, {'level': 1, 'hidden': True})
ws.set_row(3, None, None, {'level': 1, 'hidden': True})
ws.set_row(4, None, None, {'level': 1, 'hidden': True})
ws.set_row(5, None, None, {'level': 1, 'hidden': True})
ws.set_row(6, None, None, {'level': 1, 'hidden': True})
ws.set_row(7, None, None, {'collapsed': True})
	
wb.close()
print("OK")
print("Saved to: "+str(Path(str(Path(res_file).parent)+'/'+str(Path(res_file).stem)+'.xlsx')))
