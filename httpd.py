#!/usr/bin/env python
# -*- coding: utf-8 -*-
# httpd.py
"""
Author:         hong jianqiang <569250030@qq.com>
Filename:       httpd.py
Last modified:  2015-07-28 21:00

Description:
    拓展python的SimpleHTTPServer，支持断点续传
    参考文献：
    http://blog.xiaket.org/2011/extending-simplehttpserver.html
"""

import os, socket

from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler



class NotracebackServer(HTTPServer):
	"""
	could make this a mixin, but decide to keep it simple for a simple script.
	"""
	def handle_error(self, *args):
		"""override default function to disable traceback."""
		pass



class PartialContentHandler(SimpleHTTPRequestHandler):
	def send_head(self):
		"""Common code for GET and HEAD commands.

		This sends the response code and MIME headers.

		Return value is either a file object (which has to be copied
		to the outputfile by the caller unless the command was HEAD,
		and must be closed by the caller under all circumstances), or
		None, in which case the caller has nothing further to do.

		"""
		path = self.translate_path(self.path)
		f = None
		if os.path.isdir(path):
			if not self.path.endswith('/'):
				# redirect browser - doing basically what apache does
				self.send_response(301)
				self.send_header("Location", self.path + "/")
				self.end_headers()
				return None
			for index in "index.html", "index.htm":
				index = os.path.join(path, index)
				if os.path.exists(index):
					path = index
					break
			else:
				return self.list_directory(path)
		ctype = self.guess_type(path)
		try:
			# Always read in binary mode. Opening files in text mode may cause
			# newline translations, making the actual size of the content
			# transmitted *less* than the content-length!
			f = open(path, 'rb')
			fs = os.fstat(f.fileno())
		except IOError:
			self.send_error(404, "File not found")
			return None

		# 增加的断点续传功能
		if self.headers.get("Range"):
			Range = self.headers.get("Range")
			tmp1  = Range.split("=")
			tmp2  = tmp1[1].split("-")
			start = int(tmp2[0])
			end   = int(tmp2[1]) if 2==len(tmp2) else 0
			step  = 0
			if end > start:
				step = end - start
			else:
				step = fs[6] - start
			self.send_response(206)
			self.send_header("Content-type", ctype)
			#self.send_header("Connection", "keep-alive")
			full = fs.st_size
			self.send_header("Content-Length", str(fs[6] - start))
			self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
			Range = Range.replace("=", " ")
			self.send_header("Content-Range", "%s/%s" % (Range, full-1))
			self.end_headers()
			f.seek(start)
			try:
				#self.copyfile(f, self.wfile)
				buf = f.read(step)
				self.wfile.write(buf)
				self.log_message('"%s" %s', self.requestline, "req finished.")
			except socket.error:
				self.log_message('"%s" %s', self.requestline, "req terminated.")
			finally:
				f.close()
			return None

		try:
			self.send_response(200)
			self.send_header("Content-type", ctype)
			# fs = os.fstat(f.fileno())
			self.send_header("Content-Length", str(fs[6]))
			self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
			self.end_headers()
			return f
		except:
			f.close()
			raise
		


def main(port, server_class=NotracebackServer, handler_class=PartialContentHandler):
	server_address = ('', port)
	httpd = server_class(server_address, handler_class)
	httpd.serve_forever()


if '__main__' == __name__:
	port 	= 81
	ip 		= socket.gethostbyname(socket.gethostname())
	print 'serving on: http://%s:%s/' % (ip, port)
	print "===== start logging =====\n"
	main(port=port)