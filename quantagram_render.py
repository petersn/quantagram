#! /usr/bin/python

import re
import math

begin_env = re.compile(r"\\begin\s*[{]quantagram[}]", re.MULTILINE)
end_env = re.compile(r"\\end\s*[{]quantagram[}]", re.MULTILINE)
quantagram_options = re.compile(r"\\quantagramoptions\s*[{]([^}]*)[}]", re.MULTILINE)
drawing_tikz_header = r"""
\begin{tikzpicture}[thick,rotate=%(rotate)s,xscale=1,yscale=%(yscale)s,cross/.style={path picture={ 
  \draw[black]
(path picture bounding box.south) -- (path picture bounding box.north) (path picture bounding box.west) -- (path picture bounding box.east);
}},fredkinex/.style={path picture={ 
  \draw[black]
(path picture bounding box.south east) -- (path picture bounding box.north west) (path picture bounding box.south west) -- (path picture bounding box.north east);
}}]
\tikzstyle{operator} = [draw,fill=blue!10,minimum size=1.5em] 
\tikzstyle{phase} = [draw,fill,shape=circle,minimum size=5pt,inner sep=0pt]
\tikzstyle{surround} = [fill=white,thick,draw=black,rounded corners=2mm]
\matrix[row sep=%(row-sep)s, column sep=%(column-sep)s] (circuit) {
"""

def error(s):
	print "="*len(s)
	print s
	print "="*len(s)
	exit(1)

def remove_latex_comments(s):
	"""remove_latex_comments(s) -> s, but after a really crummy attempt to remove comments"""
	bilge = "RaNdOmNoNcE"
	return "\n".join(i.replace("\\%", bilge).split("%", 1)[0].replace(bilge, "\\%") for i in s.split("\n"))

global_config = {
	"rotate": 0,
	"flip": 0,
	"bubble": 0,
	"row-sep": "3mm",
	"column-sep": "5mm",
	"input-length": "3mm",
	"output-length": "3mm",
}
float_options = ["flip", "rotate", "bubble"]
string_options = ["row-sep", "column-sep", "input-length", "output-length"]

def global_interpret(opt):
	print "="*5, "\\quantagramoptions{%s}" % opt
	if opt == "time-up":
		global_config["rotate"] = 0
		global_config["flip"] = False
	elif opt == "time-down":
		global_config["rotate"] = 0
		global_config["flip"] = True
	elif opt == "time-left":
		global_config["rotate"] = 270
		global_config["flip"] = True
	elif opt == "time-right":
		global_config["rotate"] = 270
		global_config["flip"] = False
	elif any(opt.startswith(i+"=") for i in float_options+string_options):
		for i in float_options+string_options:
			if opt.startswith(i+"="):
				value = opt[len(i)+1:]
				if i in float_options:
					value = float(value)
				global_config[i] = value
	else:
		error("Unknown \\quantagramoptions flag: %s" % opt)

def extract_envs(s):
	s = remove_latex_comments(s)
	# Find all the options passed.
	for opts in quantagram_options.findall(s):
		opts = [i.strip() for i in opts.split(",") if i.strip()]
		map(global_interpret, opts)
	envs = []
	while True:
		match = begin_env.search(s)
		if not match: break
		s = s[match.end():]
		match = end_env.search(s)
		if not match:
			error("Unterminated quantagram environment!")
		envs.append(s[:match.start()])
		s = s[match.end():]
	return envs

class Node:
	def __init__(self, x, bit, type_of, code):
		self.x, self.bit, self.type_of, self.code = x, bit, type_of, code

	def to_code(self):
		if self.type_of == "node":
			s = r"\node"
		elif self.type_of == "op":
			s = r"\node[operator]"
		elif self.type_of == "dot":
			s = r"\node[phase]"
		elif self.type_of == "plus":
			s = r"\node[draw,circle,cross]"
		elif self.type_of == "x":
			s = r"\node[fredkinex]"
		else: assert False
		s += " (xy%ib%i) {\ensuremath{%s}};" % (self.x, self.bit, self.code)
		return s

class Line:
	def __init__(self, x1, bit1, x2, bit2):
		self.x1, self.bit1, self.x2, self.bit2 = x1, bit1, x2, bit2

class BracketDecoration:
	def __init__(self, low, high, code, direction):
		self.low, self.high, self.code, self.direction = low, high, code, direction

	def to_code(self, d):
		y_shift = "0.5mm" if self.low != self.high else "2mm"
		x_shift = "1mm" if self.direction == "right" else "-1mm"
		x = d.maximum_x if self.direction == "right" else 1
		do_mirror = "" if self.direction == "right" else ",mirror"
		node_name = d.new_node_name()
		return (r"""\draw[decorate,decoration={brace%s},thick]
($(xy%ib%i.east)+(%s,%s)$)
to node[midway,%s] (%s) {$\displaystyle %s$}
($(xy%ib%i.east)+(%s,-%s)$);
""" % (do_mirror, x, self.low, x_shift, y_shift, self.direction, node_name, self.code, x, self.high, x_shift, y_shift), [node_name])

class Drawing:
	def __init__(self):
		self.nodes = []
		self.lines = []
		self.decos = []
		self.node_name_index = 0

	def new_node_name(self):
		self.node_name_index += 1
		return "dynnode%i" % self.node_name_index

	def add_node(self, n):
		self.nodes.append(n)

	def add_line(self, l):
		self.lines.append(l)

	def add_deco(self, d):
		self.decos.append(d)

	def compute(self):
#		self.maximum_x = max(n.x for n in self.nodes)
		self.row_count = 0
		if self.nodes:
			self.row_count = max(self.row_count, max(n.bit for n in self.nodes))
		if self.decos:
			self.row_count = max(self.row_count, max(d.high for d in self.decos))

	def to_code(self):
		self.compute()
		s = drawing_tikz_header % global_config
		# Draw the matrix row by row.
		for bit in xrange(1, self.row_count+1):
			for x in xrange(1, self.maximum_x+1):
				for node in self.nodes:
					if node.bit != bit or node.x != x:
						continue
					# Now we render the node.
					s += node.to_code()
					break
				else:
					# Make sure there's at least a place keeper node.
					s += "\\coordinate (xy%ib%i);" % (x, bit)
				s += " &\n"
			s += "\\coordinate (end%i);\\\\\n" % bit
		s += "};\n"
		# Now, add on doodads in the background layer.
		fit_list = ["(xy%ib%i)" % (x, bit) for x in xrange(1, self.maximum_x+1) for bit in xrange(1, self.row_count+1)]
		s += r"\begin{pgfonlayer}{qg2}"
		# Draw the horizontal lines.
		for bit in xrange(1, self.row_count+1):
			s += "\\draw[thick] (xy1b%i) -- (xy%ib%i);\n" % (bit, self.maximum_x, bit)
		# Draw the interaction lines.
		for line in self.lines:
			s += "\\draw[thick] (xy%ib%i.center) -- (xy%ib%i.center);\n" % (line.x1, line.bit1, line.x2, line.bit2)
		for deco in self.decos:
			new_code, new_nodes = deco.to_code(self)
			s += new_code
			for n in new_nodes:
				fit_list.append("(%s)" % n)
		s += "\\end{pgfonlayer}\n"
		if global_config["bubble"]:
			s += "\\begin{pgfonlayer}{qg1}\n"
			s += "\\node[surround] (supernode) [fit = %s] {};"% " ".join(fit_list)
			s += "\\end{pgfonlayer}\n" 
		s += "\\end{tikzpicture}\n"
		return s

def compile_quantagram_code(code):
	d = Drawing()
	code = code.replace(";", "\n").split("\n")
	x = 1
	for line in code:
		line = line.split("%")[0].strip()
		if not line: continue
		line = line.split(" ")
		cmd, args = line[0], line[1:]
		if cmd in ("node", "op"):
			# Get the coordinate of the node.
			bit = int(args[0])
			# All remaining text (rejoined) is the code.
			code = " ".join(args[1:])
			d.add_node(Node(x, bit, cmd, code))
		elif cmd == "cnot":
			control = int(args[0])
			flip = int(args[1])
			d.add_node(Node(x, control, "dot", ""))
			d.add_node(Node(x, flip, "plus", ""))
			d.add_line(Line(x, control, x, flip))
		elif cmd == "toffoli":
			c1 = int(args[0])
			c2 = int(args[1])
			flip = int(args[2])
			d.add_node(Node(x, c1, "dot", ""))
			d.add_node(Node(x, c2, "dot", ""))
			d.add_node(Node(x, flip, "plus", ""))
			d.add_line(Line(x, c1, x, c2))
			d.add_line(Line(x, c2, x, flip))
		elif cmd == "fredkin":
			control = int(args[0])
			swap1 = int(args[1])
			swap2 = int(args[2])
			d.add_node(Node(x, control, "dot", ""))
			d.add_node(Node(x, swap1, "x", ""))
			d.add_node(Node(x, swap2, "x", ""))
			d.add_line(Line(x, control, x, swap1))
			d.add_line(Line(x, swap1, x, swap2))
		elif cmd == "next":
			x += 1
		elif cmd in ("start-def", "end-def"):
			low, high = int(args[0]), int(args[1])
			code = " ".join(args[2:])
			direction = "left" if cmd == "start-def" else "right"
			d.add_deco(BracketDecoration(low, high, code, direction=direction))
		else:
			error("Invalid command: %s" % cmd)
	d.maximum_x = x
	# Do some processing on global_config.
	global_config["yscale"] = -1 if global_config["flip"] else 1
	return d.to_code()

if __name__ == "__main__":
	import sys
	if len(sys.argv) != 2:
		print "Usage: quantagram_render.py input.tex"
		exit(2)
	fd = open(sys.argv[1])
	data = fd.read()
	fd.close()
	envs = extract_envs(data)
	for i, s in enumerate(envs):
		code = compile_quantagram_code(s)
		print code
		fd = open("_quantagram_diagram%i.tex" % i, "w")
		fd.write(code)
		fd.close()

