#!/usr/bin/python
# coding=utf8

'''
Leica Log Convert
(c) 2014 Jiri Lunacek (jlunacek@gmail.com)
Released under GPL

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

import re,math,sys

# lengths 0.1mm
# horizontal angles
re_dashes = re.compile('^\-\-+$')
re_keyval = re.compile('^([a-zA-Z\s]+[^\s])\s*:(.*)$')
re_keyval2 = re.compile('^([a-zA-Z\s]+[^\s])\s*:(.*?)\s([a-zA-Z\s]+[^\s])\s*:(.*?)$')
re_mean = re.compile('^\s*([a-z0-9]+)\s+mean( distance)? of all sets.*?:\s+([0-9\.]+).*$', re.I)
re_result = re.compile('^(Hz residual|V residual|Distance Result)\s+Set:\s*([0-9]+)\s+Point ID:\s*([a-z0-9]+)\s+(reduced )?mean.*?:\s*([0-9\.]+)\s+(hz )?residuals( v)?:\s*(-?[0-9\.]+)\s*$', re.I)

emptyline_seen = False
line_position = 1

def readl(fd):
	global emptyline_seen, line_position
	line = fd.readline()
	line_position += 1
	if line == "":
		if emptyline_seen:
			raise Exception("Unexpeted EOF")
		else:
			emptyline_seen = True
	return line

def add_keyval(mydict, key, value, mytype = None):
	global line_position
	try:
		if re.match('.*(number|set$|serial no\.)', key, re.I) != None or mytype == 'number':
			mydict[key] = int(value)
		elif re.match('.*(deviation|residual|mean)',key,re.I) != None or mytype == 'float':
			mydict[key] = float(value)
		else:
			mydict[key] = value
	except:
		print "Line: %d, key: %s, value: %s" % (line_position, key, value)
		raise
		
def print_gnet_formated(data_set):
	global line_number
	if data_set.has_key('Distance'):
		for point in data_set['Points']:
			for i in range(len(data_set['Distance']['Results'][point])):
				distance = data_set['Distance']['Results'][point][i]['Mean']
				distance = distance * math.sin(data_set['Vertical']['Results'][point][i]['Mean']*math.pi/200)
				if distance < 1000:
					distpart = "18+%08d" % (distance*100000,)
				else:
					distpart = "16+%08d" % (distance*10000,)
				print "11%04d+%04s%04s   32..%s" % (line_number, data_set['Header']['Station'].zfill(4), point.zfill(4),distpart)
				line_number += 1
	# distance end
	if data_set.has_key('Horizontal'):
		# horizontal follows
		angle_start = data_set['Horizontal']['Means'][data_set['Points'][0]]
		for point in data_set['Points']:
			if point == data_set['Points'][0]:
				print "41%04d+%04s%04s   42....+%08d" % (line_number, data_set['Header']['Station'].zfill(4), point.zfill(4), int(data_set['Horizontal']['Means'][point]*100000))
			else:
				print "41%04d+%04s%04s   42....+%08d      44....+%08d" % (line_number, data_set['Header']['Station'].zfill(4), point.zfill(4), int(data_set['Horizontal']['Means'][point]*100000), 
					int(data_set['Horizontal']['Header']['standard deviation of all measurements']*100000)
				)
			line_number += 1
		print "41%04d+00001000   42....+00000000" % (line_number,)
		line_number += 1
			

def find_header(fd, dashes_read = False):
	global line_position
	if dashes_read:
		dashes = 1
	else:
		dashes = 0
	line = fd.readline()
	line_position += 1
	if line == "":
		return None
	found = False
	caption_lines = 0
	header = {}
	while True:
		if re_dashes.match(line.strip()):
			if dashes == 0:
				# header caption
				dashes += 1
				caption_lines = 0
			elif dashes > 1:
				# we came to an end (tps station) and yet we found another line of dashes - reset
				dashes = 0
				caption_lines = 0
				header = {}
			else:
				#will parse header now
				dashes += 1
				found = True
		elif dashes == 1:
			if caption_lines > 1:
				# more than one heading line - this is strange - reset
				header = {}
				dashes = 0
				caption_lines = 0
			else:
				caption_lines += 1
				header['Format'] = line.strip()
		elif found == True:
			if line.strip() != "":
				mymatch = re_keyval.match(line.strip())
				if mymatch != None:
					if mymatch.group(1).strip() == 'TPS Station':
						d = mymatch.group(2).strip().split('\t')
						header['Station'] = d.pop(0).strip()
						d = dict(map(lambda x:(x.split('=')[0].strip(),float(x.split('=')[1].strip())),d))
						header[mymatch.group(1).strip()] = d
						return header
					else:
						add_keyval(header,mymatch.group(1).strip(),mymatch.group(2).strip())
		else:
			pass
		line = fd.readline()
		line_position += 1
		if line == "":
			if dashes == 0:
				return None
			else:
				raise Exception('Unexpected EOF')


def parse_file(fd):
	global line_number, dashes_read
	line_number = 1
	dashes_read = False
	while True:
		data_set = {}
		data_set['Header'] = find_header(fd, dashes_read)
		dashes_read = False
		if data_set['Header'] == None:
			break
		line = readl(fd)
		mymatch = re_dashes.match(line.strip())
		if mymatch == None:
			#empty data set
			continue
		else:
			results_to_search = ['Horizontal Set Results', 'Vertical Set Results', 'Distance Results']
			#scan for results
			while len(results_to_search):
				result_type = None
				result_header = {}
				while True:
					line = readl(fd).strip()
					if line in results_to_search:
						result_type = line.split()[0]
						results_to_search.remove(line)
						break
					elif re_dashes.match(line) != None:
						# end of data set
						dashes_read = True
						break
						raise Exception('Invalid data format. Line %d:' % (line_position,) + line)
				if dashes_read:
					break
				# cteme hlavicku resultu
				while True:
					line = readl(fd)
					mymatch = re_keyval.match(line.strip())
					mymatch2 = re_keyval2.match(line.strip())
					mymatch_dashes = re_dashes.match(line.strip())
					if mymatch2 != None:
						add_keyval(result_header,mymatch2.group(1).strip().lower(), mymatch2.group(2).strip())
						add_keyval(result_header,mymatch2.group(3).strip().lower(), mymatch2.group(4).strip())
					elif mymatch != None:
						add_keyval(result_header, mymatch.group(1).strip().lower(), mymatch.group(2).strip())
					elif mymatch_dashes != None:
						break
				result_means = {}
				results = {}
				points = []
				while True:
					line = readl(fd)
					mymatch = re_mean.match(line.strip())
					if mymatch != None:
						points.append(mymatch.group(1))
						add_keyval(result_means, mymatch.group(1), mymatch.group(3), 'float')
					elif line.strip() == "":
						continue
					else:
						mymatch = re_result.match(line.strip())
						if mymatch != None:
							break
				for i in range(result_header['number of sets'] * result_header['number of points']):
					# mymatch jiz obsahuje prvni radek vysledku
					if not results.has_key(mymatch.group(3)):
						results[mymatch.group(3)] = []
					results[mymatch.group(3)].append({
						'Set': int(mymatch.group(2)),
						'Mean': float(mymatch.group(5)),
						'Residual': float(mymatch.group(8))
					})
					line = readl(fd)
					mymatch = re_result.match(line.strip())
					if mymatch == None:
						break
				if data_set.has_key('Points'):
					if data_set['Points'] != points:
						print data_set
						print data_set['Points']
						print points
						raise Exception('List of points differs!!! Line %d' % line_position)
				else:
					data_set['Points'] = points
				data_set[result_type] = {'Means':result_means, 'Results':results, 'Header': result_header}
			print_gnet_formated(data_set)


if __name__ == "__main__":
	parse_file(sys.stdin)





